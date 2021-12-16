#!/usr/bin/env bash

# begin configuration section
stage=1
nj=4
workdir=align
data=
meta=
oov="<unk>"
boost_silence=1.0
strip_pos=false
# end configuration section

help_message="$0: Main alignment script for KISS Aligner
Options:
  --stage 1            # starting point for partial re-runs
  --nj 4               # number of parallel jobs
  --workdir align      # output directory for alignment files
  --oov '<unk>'        # symbol to use for out-of-vocabulary items
  --boost-silence 1.0  # factor to boost silence models (none by default)
  --strip-pos false    # strip word position labels from phone CTM outputs"

. ./cmd.sh          # set train_cmd for parallel jobs
. ./path.sh         # set PATH and environment variables
. parse_options.sh  # parse command line options

set -e

# TODO: some smart handling of input metadata filenames to name 
# align/data/$part subdirectories
#meta_base=${meta##*/}
#part=${meta%.*}

# TODO: try and set up data/ and lang/ directories from input metadata file
# and lexicon in standard formats
#if [ $stage -le 1 ]; then
#  mkdir -p $workdir/{data/$part,lang}
#fi

if [ $stage -le 1 ]; then
  # TODO: check data/train/text for OOV against data/local/dict/lexicon.txt
  utils/prepare_lang.sh $workdir/data/local/dict \
    "$oov" $workdir/data/local/lang $workdir/data/lang
fi

if [ $stage -le 2 ]; then
  steps/make_mfcc.sh --cmd "$train_cmd" --nj $nj \
    $workdir/data/train $workdir/data/train/mfcc $workdir/data/train/mfcc
  steps/compute_cmvn_stats.sh $workdir/data/train \
    $workdir/data/train/mfcc $workdir/data/train/mfcc
  # clear out any missing data
  utils/fix_data_dir.sh $workdir/data/train
fi

if [ $stage -le 3 ]; then
  # Make some small data subsets for early system-build stages. For the
  # monophone stages we select the shortest utterances by duration, which
  # should make it easier to align the data from a flat start (maybe be careful
  # about this in case there are repeated prompts across speakers).
  # TODO: Make these split sizes configurable (will fail if not enough utterances)
  utils/validate_data_dir.sh $workdir/data/train
  utils/subset_data_dir.sh --shortest $workdir/data/train 2000 $workdir/data/train_2kshort
  utils/subset_data_dir.sh $workdir/data/train 5000 $workdir/data/train_5k
  utils/subset_data_dir.sh $workdir/data/train 10000 $workdir/data/train_10k
fi

if [ $stage -le 4 ]; then
  # train a monophone system
  steps/train_mono.sh --nj $nj --cmd "$train_cmd" --boost-silence $boost_silence \
    $workdir/data/train_2kshort $workdir/data/lang $workdir/exp/mono
  # align next training subset
  steps/align_si.sh --nj $nj --cmd "$train_cmd" --boost-silence $boost_silence \
    $workdir/data/train_5k $workdir/data/lang $workdir/exp/mono $workdir/exp/mono_ali_5k
fi

if [ $stage -le 5 ]; then
  # train a first delta + delta-delta triphone system on a subset of 5000 utterances
  steps/train_deltas.sh --cmd "$train_cmd" --boost-silence $boost_silence \
    2000 10000 $workdir/data/train_5k $workdir/data/lang $workdir/exp/mono_ali_5k $workdir/exp/tri1
  steps/align_si.sh --nj $nj --cmd "$train_cmd" \
    $workdir/data/train_10k $workdir/data/lang $workdir/exp/tri1 $workdir/exp/tri1_ali_10k
fi

if [ $stage -le 6 ]; then
  # train an LDA+MLLT system.
  steps/train_lda_mllt.sh --cmd "$train_cmd" \
    --splice-opts "--left-context=3 --right-context=3" 2500 15000 \
    $workdir/data/train_10k $workdir/data/lang $workdir/exp/tri1_ali_10k $workdir/exp/tri2b
  # align a 10k utts subset using the tri2b model
  steps/align_si.sh  --nj $nj --cmd "$train_cmd" --use-graphs true \
    $workdir/data/train_10k $workdir/data/lang $workdir/exp/tri2b $workdir/exp/tri2b_ali_10k
fi

if [ $stage -le 7 ]; then
  # train tri3b, which is LDA+MLLT+SAT on 10k utts
  steps/train_sat.sh --cmd "$train_cmd" 2500 15000 \
    $workdir/data/train_10k $workdir/data/lang $workdir/exp/tri2b_ali_10k $workdir/exp/tri3b
  # align the entire train_clean_100 subset using the tri3b model
  steps/align_fmllr.sh --nj $nj --cmd "$train_cmd" \
    $workdir/data/train $workdir/data/lang \
    $workdir/exp/tri3b $workdir/exp/tri3b_ali_train
fi

if [ $stage -le 8 ]; then
  # train another LDA+MLLT+SAT system on the entire 100 hour subset
  steps/train_sat.sh  --cmd "$train_cmd" 4200 40000 \
    $workdir/data/train $workdir/data/lang \
    $workdir/exp/tri3b_ali_train $workdir/exp/tri4b
  # align train_clean_100 using the tri4b model
  steps/align_fmllr.sh --nj $nj --cmd "$train_cmd" \
    $workdir/data/train $workdir/data/lang $workdir/exp/tri4b $workdir/exp/tri4b_ali_train
fi

if [ $stage -le 9 ]; then
  # get word- and phone-level CTM files from final alignments
  steps/get_train_ctm.sh --cmd "$train_cmd" --print-silence true \
    $workdir/data/train $workdir/data/lang $workdir/exp/tri4b_ali_train
  local/get_phone_ctm.sh --cmd "$train_cmd" \
    $workdir/data/lang $workdir/exp/tri4b_ali_train
fi

if [ $stage -le 10 ]; then
  # split CTM files for final per-utterance outputs
  [ $strip_pos == true ] && strip_pos="--strip-pos" || strip_pos=""
  local/split_ctm.py $strip_pos $workdir/exp/tri4b_ali_train/ctm $workdir/word
  local/split_ctm.py $strip_pos $workdir/exp/tri4b_ali_train/ctm.phone $workdir/phone
fi
