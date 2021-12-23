#!/usr/bin/env bash

# Sample script to prepare `data/train/*` files for Kaldi alignment over LJ Speech

ljspeech_dir=$HOME/data/LJSpeech-1.1
split_by_chapter=false
workdir=align

. ./path.sh
. utils/parse_options.sh

train=$workdir/data/train
mkdir -p $train

set -euo pipefail

utts=$workdir/utts
speakers=$workdir/speakers
transcripts=$workdir/transcripts

mkdir -p $workdir
[ -f $utts ] && rm $utts
[ -f $speakers ] && rm $speakers
[ -f $transcripts ] && rm $transcripts

# Get utterance IDs
cut -d '|' -f 1 $ljspeech_dir/metadata.csv > $utts

# Treat each chapter as a separate speaker, else use single speaker ID
[ $split_by_chapter == true ] && spkr_sep='-' || spkr_sep='0'
cut -d $spkr_sep -f 1 $utts > $speakers

# Basic text cleaning (not comprehensive!)
cut -d'|' -f3 $ljspeech_dir/metadata.csv \
  | tr 'A-Z' 'a-z' \
  | perl -pe 's/\b[.,?!:;"\[\]()]/ /g;
              s/[.,?!:;"\[\]()]\b/ /g;
              s/ [-.,?!:;"\[\]()] / /g;
              s/ [-.,?!:;"\[\]()]?$//g;
              s/^[-.,?!:;"\[\]()] //g;
              s/-/ /g;
              s/ +/ /g;' \
  | perl -pe "s/ '/ /g;
              s/' / /g;
              s/'$//;
              s/^'//;" \
  > ${transcripts}

# Combine utterance IDs and cleaned transcripts
paste -d' ' $utts ${transcripts} | sort > $train/text

# Combine utterance and speaker IDs
paste -d' ' $utts $speakers | sort > $train/utt2spk
utils/utt2spk_to_spk2utt.pl $train/utt2spk > $train/spk2utt

# Write wav.scp with sox pipe to downsample audio to 16 kHz
[ -f $train/wav.scp ] && rm $train/wav.scp
while read utt; do
  audio="${ljspeech_dir}/wavs/${utt}.wav"
  printf "$utt sox -G $audio -c 1 -r 16k -e signed-integer -t wav - |\n" \
    >> $train/wav.scp
done < <(sort $utts)

rm $utts $speakers $transcripts
