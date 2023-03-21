#!/bin/bash

LITIR=egs/learngaelic_litir

# Grab long audio files and transcripts
python $LITIR/local/scrape_transcripts_and_audios.py \
  --doc-range 1 1216 $LITIR/data/text_long $LITIR/data/ogg_long

# Convert audio to consistent WAV format
mkdir $LITIR/data/wav_long
for ogg in $LITIR/data/ogg_long/*.ogg; do
  wav=${ogg##*/}
  wav=${wav/ogg/wav}
  sox $ogg -b 16 -c 1 -r 16k $LITIR/data/wav_long/$wav
done

# Split long audio files on silences at least 1.5s long
# NB. this is very slow! ~5 hours for all 1216 recordings
python3 $LITIR/local/split_audios.py --nj 8 \
  $LITIR/data/wav_long $LITIR/data/wav_chunked

# Split long text transcripts on phrase-final punctuation
# NB. before text normalisation because closing smart quotes can indicate sentence ends
mkdir $LITIR/data/text_chunked
python $LITIR/local/split_and_number_sentences.py \
  $LITIR/data/text_long $LITIR/data/text_chunked

# Approximately align audio and text chunks based on cumulative durations
mkdir -p align_dtw/data/train
python $LITIR/local/dtw_audio_and_text_lens.py \
  $LITIR/data/wav_chunked $LITIR/data/text_chunked $LITIR/align_dtw/data/train

# Normalize text transcripts and prepare other data files
python $LITIR/local/normalize_text.py \
  $LITIR/align_dtw/data/train/text_raw $LITIR/align_dtw/data/train/text
cut -d' ' -f1 $LITIR/align_dtw/data/train/text \
  | sed 's/\(.*\)/\1 \1/' > $LITIR/align_dtw/data/train/spk2utt
cp $LITIR/align_dtw/data/train/spk2utt $LITIR/align_dtw/data/train/utt2spk

# NB. setting up kaldi lang files needs a bit more care, so we ship final
# versions after modifying the output of this script
#python $LITIR/local/make_char_lex.py \
#  $LITIR/align_dtw/data/train/text $LITIR/align_dtw/data/local/dict

# Run initial alignment
# TODO: adjust nj
./run.sh --workdir egs/learngaelic_litir/align_dtw \
  --nj 8 --stage 1 --mfcc-config conf/mfcc.conf \
  --beam 10 --retry-beam 0 --careful true


# Prepare full segmentation

# Concatenate and normalise long text transcripts per recording
#$LITIR/local/txts2text.sh
mkdir -p $LITIR/segment_utts/data/long
for text in $LITIR/data/text_long/*.txt; do
  utt=${text##*/}
  utt=${utt%.txt}
  oneline=$(paste -sd' ' $txt)
  echo "$utt $oneline" >> $LITIR/segment_utts/data/long/text_long_raw
done
python $LITIR/local/normalize_text.py \
  $LITIR/segment_utts/data/long/text_long_raw $LITIR/segment_utts/data/long/text

cut -d' ' -f1 $LITIR/segment_utts/data/long/text \
  | sed 's/\(.*\)/\1 \1/' > $LITIR/segment_utts/data/long/spk2utt
cp $LITIR/segment_utts/data/long/spk2utt $LITIR/segment_utts/data/long/utt2spk

while read utt; do
  echo "${utt} ${LITIR}/data/wav_long/${utt}.wav" >> $LITIR/segment_utts/data/long/wav.scp
done < <(cut -d' ' -f1 $LITIR/segment_utts/data/long/text)

# Run segmentation
# TODO: nj, mfcc.conf
./local/run_segment_long_utts.sh --nj 8 --stage 1 \
  --uniform-segment-length 60 --uniform-segment-overlap 15 \
  --min-segment-length 5 --max-segment-length 15 --hard-max-segment-length 20 \
  --min-silence-length 0.8 --max-silence-length 1.2 \
  --allow-repetitions true \
  --beam 10 --retry-beam 0 --careful true \
  --mfcc-config conf/mfcc.conf --ctm-output true \
  $LITIR/segment_utts $LITIR/segment_utts/data/long \
  $LITIR/align_dtw/exp/tri4b $LITIR/align_dtw/data/lang
