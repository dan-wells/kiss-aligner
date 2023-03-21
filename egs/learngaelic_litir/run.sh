#!/bin/bash

. ../../cmd.sh
. ../../path.sh

set -euo pipefail

# Grab long audio files and transcripts
local/scrape_transcripts_and_audios.py \
  --doc-range 1 1216 data/text_long data/ogg_long

# Convert audio to consistent WAV format
mkdir -p data/wav_long
echo "Converting audio files..."
for ogg in data/ogg_long/*.ogg; do
  wav=${ogg##*/}
  wav=${wav/ogg/wav}
  sox -G $ogg -b 16 -c 1 -r 16k data/wav_long/$wav
done

# Split long audio files on silences at least 1.5s long
local/split_audios.py --nj 8 \
  data/wav_long data/wav_chunked

# Split long text transcripts on phrase-final punctuation
# NB. before text normalisation because closing smart quotes can indicate sentence ends
mkdir -p data/text_chunked
local/split_and_number_sentences.py \
  data/text_long data/text_chunked

# Approximately align audio and text chunks based on cumulative durations
mkdir -p align_dtw/data/train
local/dtw_audio_and_text_lens.py \
  $PWD/data/wav_chunked data/text_chunked align_dtw/data/train

# Normalize text transcripts and prepare other data files
local/normalize_text.py \
  align_dtw/data/train/text_raw align_dtw/data/train/text
cut -d' ' -f1 align_dtw/data/train/text \
  | sed 's/\(.*\)/\1 \1/' > align_dtw/data/train/spk2utt
cp align_dtw/data/train/spk2utt align_dtw/data/train/utt2spk

# NB. setting up kaldi lang files needs a bit more care, so we ship final
# versions after modifying the output of this script
#local/make_char_lex.py \
#  align_dtw/data/train/text align_dtw/data/local/dict

# Run initial alignment
# TODO: adjust nj
pushd ../..
./run.sh --workdir egs/learngaelic_litir/align_dtw \
  --nj 8 --stage 1 --mfcc-config conf/mfcc.conf \
  --beam 10 --retry-beam 0 --careful true
popd


# Prepare full segmentation

# Concatenate and normalise long text transcripts per recording
mkdir -p segment_utts/data/long
for text in data/text_long/*.txt; do
  utt=${text##*/}
  utt=${utt%.txt}
  oneline=$(paste -sd' ' $text)
  echo "$utt $oneline" >> segment_utts/data/long/text_long_raw
done
local/normalize_text.py \
  segment_utts/data/long/text_long_raw segment_utts/data/long/text

cut -d' ' -f1 segment_utts/data/long/text \
  | sed 's/\(.*\)/\1 \1/' > segment_utts/data/long/spk2utt
cp segment_utts/data/long/spk2utt segment_utts/data/long/utt2spk

while read utt; do
  echo "${utt} $PWD/data/wav_long/${utt}.wav" >> segment_utts/data/long/wav.scp
done < <(cut -d' ' -f1 segment_utts/data/long/text)

# Run segmentation
# TODO: nj, mfcc.conf
pushd ../..
./local/run_segment_long_utts.sh --nj 8 --stage 1 \
  --uniform-segment-length 60 --uniform-segment-overlap 15 \
  --min-segment-length 5 --max-segment-length 15 --hard-max-segment-length 20 \
  --min-silence-length 0.8 --max-silence-length 1.2 \
  --allow-repetitions true \
  --beam 10 --retry-beam 0 --careful true \
  --mfcc-config conf/mfcc.conf --ctm-output true \
  egs/learngaelic_litir/segment_utts egs/learngaelic_litir/segment_utts/data/long \
  egs/learngaelic_litir/align_dtw/exp/tri4b egs/learngaelic_litir/align_dtw/data/lang
popd
