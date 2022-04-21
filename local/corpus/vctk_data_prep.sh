#!/usr/bin/env bash

# Sample script to prepare `data/train/*` files for Kaldi alignment over VCTK v0.92 data

vctk_dir=$HOME/data/vctk-0.92
workdir=align

. ./path.sh
. utils/parse_options.sh

train=$workdir/data/train
mkdir -p $train

set -euo pipefail

transcripts=$workdir/transcripts
speakers=$workdir/speakers
utts=$workdir/utts

mkdir -p $workdir
[ -f $transcripts ] && rm $transcripts
[ -f $speakers ] && rm $speakers
[ -f $utts ] && rm $utts

# Get audio files and text transcripts
for spkr_dir in $vctk_dir/txt/*; do
  spkr=${spkr_dir##*/}
  echo "$spkr"
  for txt in $spkr_dir/*; do
    utt=${txt##*/}
    utt=${utt%.txt}
    audio="$vctk_dir/wav48_silence_trimmed/${spkr}/${utt}_mic1.flac"
    if [ -f $audio ] && [ -f $txt ]; then
      echo $spkr >> $speakers
      echo $utt >> $utts
      # some transcripts (p376) have no line terminators:
      # this sed incantation adds them if missing
      cat $txt | sed -e '$a\' >> $transcripts
    fi
  done
done

# Basic text cleaning
cat $transcripts \
  | tr 'A-Z' 'a-z' \
  | perl -pe 's/\b[.,?!]/ /g;
              s/[.,?!]\b/ /g;
              s/ [-.,?!] / /g;
              s/ [-.,?!]?$//g;
              s/^[-.,?!] //g;
              s/`\t//g;
              s/ +/ /g;' \
  > ${transcripts}_clean

# Combine utterance IDs and cleaned transcripts
paste -d' ' $utts ${transcripts}_clean | sort > $train/text

# Combine utterance and speaker IDs
paste -d' ' $utts $speakers | sort > $train/utt2spk
utils/utt2spk_to_spk2utt.pl $train/utt2spk > $train/spk2utt

# Write wav.scp with sox pipe to convert flac to wav and downsample to 16 kHz
[ -f $train/wav.scp ] && rm $train/wav.scp
while read utt; do
  audio="${vctk_dir}/wav48_silence_trimmed/${utt%_*}/${utt}_mic1.flac"
  printf "$utt sox -G $audio -c 1 -r 16k -e signed-integer -t wav - |\n" \
    >> $train/wav.scp
done < <(sort $utts)

rm $utts $speakers $transcripts ${transcripts}_clean
