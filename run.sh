#!/usr/bin/env bash

# begin configuration section
meta=
lex=
audio_root=
workdir=align
oov='<unk>,SPN'
exit_on_oov=false
resample=0
resample_method=sox
mfcc_config=conf/mfcc.conf
spkr_sep='-'
spkr_in_wav=false
meta_field_sep=' '
lex_field_sep=' '
boost_silence=1.0
strip_pos=false
textgrid_output=false
stage=0
nj=4
# end configuration section

help_message="$0: Main alignment script for KISS Aligner
Options:
  --meta                        # metadata file with audio paths and transcripts
  --lex                         # lexicon file
  --audio-root                  # longest common path for audio files in meta
  --workdir align               # output directory for alignment files
  --oov '<unk>,SPN'             # symbol to use for out-of-vocabulary items
  --exit-on-oov false           # stop early if OOV items found in training data
  --resample 16000              # convert audio to new sampling rate (off by default)
  --resample-method sox         # tool to resample audio (sox|ffmpeg|kaldi)
  --mfcc-config conf/mfcc.conf  # config file for mfcc extraction
  --spkr-sep '-'                # character joining speaker prefix to utterance IDs
  --spkr-in-wav false           # speaker prefix already part of audio filenames
  --meta-field-sep ' '          # field separator in metadata file
  --lex-field-sep ' '           # field separator in lexicon
  --boost-silence 1.0           # factor to boost silence models (none by default)
  --strip-pos false             # strip word position labels from phone CTM outputs
  --textgrid-output false       # also write alignments to Praat TextGrid format
  --stage 0                     # starting point for partial re-runs
  --nj 4                        # number of parallel jobs"

. ./cmd.sh          # set train_cmd for parallel jobs
. ./path.sh         # set PATH and environment variables
. parse_options.sh  # parse command line options

set -euo pipefail

data=$workdir/data
exp=$workdir/exp

# TODO: some smart handling of input metadata filenames to name 
# align/data/$part subdirectories
#meta_base=${meta##*/}
#part=${meta%.*}

if [ $stage -le 0 ]; then
  # prepare data files from metadata input
  [ $spkr_in_wav == true ] && spkr_in_wav="--spkr-in-wav" || spkr_in_wav=""
  [ -n $meta ] && local/prep_data.py \
    $meta $audio_root --workdir $workdir \
    --resample $resample --resample-method $resample_method \
    $spkr_in_wav --spkr-sep "$spkr_sep" --field-sep "$meta_field_sep"
  # prepare dictionary files from lexicon input
  [ -n $lex ] && local/prep_dict.py \
    $lex --workdir $workdir --oov ${oov/,/ } \
    --field-sep "$lex_field_sep"
fi

if [ $stage -le 1 ]; then
  [ $exit_on_oov = true ] && warn_on_oov="--warn-on-oov" || warn_on_oov=""
  local/check_oov.py --workdir $workdir \
    $data/lang/words.txt $data/train/text \
    $warn_on_oov || (echo "Check OOV files: $workdir/oov_{words,utts}.txt"; exit 1)
  utils/prepare_lang.sh $data/local/dict \
    ${oov%,*} $data/local/lang $data/lang
fi

if [ $stage -le 2 ]; then
  [ "$resample_method" == "kaldi" ] && mfcc_config=$workdir/conf/mfcc.conf
  steps/make_mfcc.sh --cmd "$train_cmd" --nj $nj \
    --mfcc-config $mfcc_config \
    $data/train $data/train/mfcc $data/train/mfcc
  steps/compute_cmvn_stats.sh \
    $data/train $data/train/mfcc $data/train/mfcc
  # clear out any missing data
  utils/fix_data_dir.sh $data/train
fi

if [ $stage -le 3 ]; then
  # Make some small data subsets for early system-build stages. For the
  # monophone stages we select the shortest utterances by duration, which
  # should make it easier to align the data from a flat start (maybe be careful
  # about this in case there are repeated prompts across speakers).
  # TODO: Make these split sizes configurable (will fail if not enough utterances)
  utils/validate_data_dir.sh $data/train
  utils/subset_data_dir.sh --shortest $data/train 2000 $data/train_2kshort
  utils/subset_data_dir.sh $data/train 5000 $data/train_5k
  utils/subset_data_dir.sh $data/train 10000 $data/train_10k
fi

if [ $stage -le 4 ]; then
  # train a monophone system on 2k short utts
  steps/train_mono.sh --nj $nj --cmd "$train_cmd" \
    --boost-silence $boost_silence \
    $data/train_2kshort $data/lang $exp/mono
  # align next training subset
  steps/align_si.sh --nj $nj --cmd "$train_cmd" \
    --boost-silence $boost_silence \
    $data/train_5k $data/lang $exp/mono $exp/mono_ali_5k
fi

if [ $stage -le 5 ]; then
  # train a first delta + delta-delta triphone system on a subset of 5000 utterances
  steps/train_deltas.sh --cmd "$train_cmd" \
    --boost-silence $boost_silence \
    2000 10000 \
    $data/train_5k $data/lang $exp/mono_ali_5k $exp/tri1
  steps/align_si.sh --nj $nj --cmd "$train_cmd" \
    $data/train_10k $data/lang $exp/tri1 $exp/tri1_ali_10k
fi

if [ $stage -le 6 ]; then
  # train an LDA+MLLT system on 10k utts
  steps/train_lda_mllt.sh --cmd "$train_cmd" \
    --splice-opts "--left-context=3 --right-context=3" 2500 15000 \
    $data/train_10k $data/lang $exp/tri1_ali_10k $exp/tri2b
  # align a 10k utts subset using the tri2b model
  steps/align_si.sh  --nj $nj --cmd "$train_cmd" \
    --use-graphs true \
    $data/train_10k $data/lang $exp/tri2b $exp/tri2b_ali_10k
fi

if [ $stage -le 7 ]; then
  # train tri3b, which is LDA+MLLT+SAT on 10k utts
  steps/train_sat.sh --cmd "$train_cmd" \
    2500 15000 \
    $data/train_10k $data/lang $exp/tri2b_ali_10k $exp/tri3b
  # align the entire train_clean_100 subset using the tri3b model
  steps/align_fmllr.sh --nj $nj --cmd "$train_cmd" \
    $data/train $data/lang $exp/tri3b $exp/tri3b_ali_train
fi

if [ $stage -le 8 ]; then
  # train another LDA+MLLT+SAT system on the entire data set
  steps/train_sat.sh  --cmd "$train_cmd" \
    4200 40000 \
    $data/train $data/lang $exp/tri3b_ali_train $exp/tri4b
  # align train_clean_100 using the tri4b model
  steps/align_fmllr.sh --nj $nj --cmd "$train_cmd" \
    $data/train $data/lang $exp/tri4b $exp/tri4b_ali_train
  # check retried and failed utterances
  local/check_alignments.sh $exp/tri4b_ali_train $workdir
fi

if [ $stage -le 9 ]; then
  # get word- and phone-level CTM files from final alignments
  steps/get_train_ctm.sh --cmd "$train_cmd" \
    --print-silence true \
    $data/train $data/lang $exp/tri4b_ali_train
  local/get_phone_ctm.sh --cmd "$train_cmd" \
    $data/lang $exp/tri4b_ali_train
fi

if [ $stage -le 10 ]; then
  # split CTM files for final per-utterance outputs
  [ $strip_pos == true ] && strip_pos="--strip-pos" || strip_pos=""
  local/split_ctm.py $strip_pos $exp/tri4b_ali_train/ctm $workdir/word
  local/split_ctm.py $strip_pos $exp/tri4b_ali_train/ctm.phone $workdir/phone
  # convert alignments to Praat TextGrid format
  [ $textgrid_output == true ] && local/ctm_to_textgrid.py \
    $exp/tri4b_ali_train/ctm $exp/tri4b_ali_train/ctm.phone $workdir/TextGrid \
    --workdir $workdir
fi
