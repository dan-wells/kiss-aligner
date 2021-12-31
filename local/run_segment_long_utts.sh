#!/usr/bin/env bash

help_message="Segment long audio files given approximate transcripts

Usage:
  $0 [options] <workdir> <data> <src_model> <src_lang>
Args:
  workdir    # root directory for all outputs
  data       # directory with data to be segmented
  src_model  # directory with in-domain SAT model for alignment
  src_lang   # lang/ directory matching <src_model>
Options:
  --stage 0                     # starting point for partial re-runs
  --segment-stage 0             # starting point for segmentation script
  --nj 4                        # number of parallel jobs
  --mfcc-config conf/mfcc.conf  # config file for mfcc extraction
  --ctm-output false            # write word and phone CTM files for discovered segments
  --strip-pos true              # strip word position labels from phone CTM outputs
  --textgrid-output false       # also write alignments to Praat TextGrid format
  --exit-on-oov false           # stop early if OOV items found in transcripts

Split wavs will be output to <workdir>/wavs and discovered transcripts
written to <workdir>/text"

# begin configuration section
stage=0
segment_stage=0
nj=4
mfcc_config=conf/mfcc.conf
ctm_output=false
strip_pos=true
textgrid_output=false
exit_on_oov=false
# end configuration section

. ./cmd.sh          # set train_cmd for parallel jobs
. ./path.sh         # set PATH and environment variables
. parse_options.sh  # parse command line options

set -euo pipefail

workdir=$1
data=$2
src_model=$3
src_lang=$4

if [ $stage -le 0 ]; then
  # check for out-of-vocabulary items in transcripts
  # note: segmentation will still work if there are OOVs, but discovered
  # segments will be cut around them
  [ $exit_on_oov = true ] && warn_on_oov="--warn-on-oov" || warn_on_oov=""
  local/check_oov.py --workdir $workdir \
    $src_lang/words.txt $data/text \
    $warn_on_oov || (echo "Check OOV files: $workdir/oov_{words,utts}.txt"; exit 1)
fi

if [ $stage -le 1 ]; then
  # prepare data to be segmented
  # TODO: input may have very few utts, so we don't try and run many
  # parallel jobs here -- could make that configurable, or use max(nj, # utts)
  steps/make_mfcc.sh --cmd "$train_cmd" --nj 1 \
    --mfcc-config $mfcc_config \
    $data $data/mfcc $data/mfcc
  steps/compute_cmvn_stats.sh \
    $data $data/mfcc $data/mfcc
fi

if [ $stage -le 2 ]; then
  # run initial segmentation
  # TODO: make these and other options below configurable
  segmentation_extra_opts=(
  --min-segment-length=5
  --min-new-segment-length=5
  --max-internal-silence-length=0.5
  --max-internal-non-scored-length=0
  --max-edge-non-scored-length=0
  --unk-padding=0
  )
  steps/cleanup/segment_long_utterances.sh --cmd "$train_cmd" --nj $nj \
    --stage $segment_stage \
    --max-segment-duration 60 --overlap-duration 10 --num-neighbors-to-search 1 \
    --max-segment-length-for-splitting 10 --hard-max-segment-length 15 \
    --min-split-point-duration 0.2 --min-silence-length-to-split-at 0.2 --min-non-scored-length-to-split-at 0.2 \
    --segmentation-extra-opts $segmentation_extra_opts \
    $src_model $src_lang $data $workdir/data_seg $workdir/exp/1-segment
fi

if [ $stage -le 3 ]; then
  # extract features and fmllr transforms over segmented data
  utils/fix_data_dir.sh $workdir/data_seg
  steps/compute_cmvn_stats.sh \
    $workdir/data_seg $workdir/data_seg $workdir/data_seg
  steps/align_fmllr.sh --cmd $train_cmd --nj $nj \
    $workdir/data_seg $src_lang $src_model $workdir/exp/2-align
fi

if [ $stage -le 4 ]; then
  # clean up initial segmentation
  segmentation_opts=(
  --min-segment-length=5
  --min-new-segment-length=5
  --min-split-point-duration=0.2
  --max-internal-silence-length=0.5
  --max-internal-non-scored-length=0
  --max-edge-non-scored-length=0
  --unk-padding=0
  )
  steps/cleanup/clean_and_segment_data.sh --cmd $train_cmd --nj $nj \
    --segmentation-opts $segmentation_opts \
    $workdir/data_seg $src_lang $workdir/exp/2-align $workdir/exp/3-cleanup $workdir/data_seg_clean
  cp $workdir/data_seg_clean/text $workdir/text
fi

if [ $stage -le 5 ]; then
  # segment audio and create split wavs
  extract-segments \
    scp:$workdir/data_seg_clean/wav.scp $workdir/data_seg_clean/segments \
    ark,scp:$workdir/exp/wav.ark,$workdir/exp/wav.scp
  echo "Splitting wav data: $workdir/exp/wav-copy.log"
  mkdir -p $workdir/wavs
  while read line; do
    utt=${line% *}
    ark=${line#* }
    wav-copy $ark $workdir/wavs/${utt}.wav 2>> $workdir/exp/wav-copy.log
  done < $workdir/exp/wav.scp
fi

if [ $stage -le 6 ]; then
  # re-align cleaned segments and summarize discovered data
  utils/data/get_utt2dur.sh $workdir/data_seg_clean
  steps/align_fmllr.sh --cmd $train_cmd --nj $nj \
    $workdir/data_seg_clean $src_lang $src_model $workdir/exp/4-align_clean
  local/check_alignments.sh $workdir/exp/4-align_clean $workdir $workdir/data_seg_clean
  # TODO: collect statistics over discovered segment lengths
fi

if [ $stage -le 7 ]; then
  if [ $ctm_output == true ]; then
    # get word- and phone-level CTM files from final alignments
    steps/get_train_ctm.sh --cmd "$train_cmd" \
      --print-silence true --use-segments false \
      $workdir/data_seg_clean $src_lang $workdir/exp/4-align_clean $workdir/data_seg_clean
    local/get_phone_ctm.sh --cmd "$train_cmd" \
      $src_lang $workdir/exp/4-align_clean $workdir/data_seg_clean
    # split CTM files for final per-utterance outputs
    [ $strip_pos == true ] && strip_pos="--strip-pos" || strip_pos=""
    local/split_ctm.py $strip_pos $workdir/data_seg_clean/ctm $workdir/word
    local/split_ctm.py $strip_pos $workdir/data_seg_clean/ctm.phone $workdir/phone
  fi
  if [ $textgrid_output == true ]; then
    # convert alignments to Praat TextGrid format
    local/ctm_to_textgrid.py \
      $workdir/data_seg_clean/ctm $workdir/data_seg_clean/ctm.phone $workdir/TextGrid \
      --workdir $workdir --datadir $workdir/data_seg_clean
  fi
fi
