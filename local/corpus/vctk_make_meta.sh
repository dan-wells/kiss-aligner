#!/usr/bin/env bash

# Sample script to prepare metadata file for VCTK v0.92 data

vctk_dir=$HOME/data/vctk-0.92
workdir=align

. ./path.sh
. utils/parse_options.sh

audios=$workdir/audios
transcripts=$workdir/transcripts
meta=$workdir/vctk_meta.raw.txt

mkdir -p $workdir
[ -f $audios ] && rm $audios
[ -f $transcripts ] && rm $transcripts
[ -f $meta ] && rm $meta

# Get audio files and text transcripts
for spkr_dir in $vctk_dir/txt/*; do
  spkr=${spkr_dir##*/}
  echo "$spkr"
  for txt in $spkr_dir/*; do
    utt=${txt##*/}
    utt=${utt%.txt}
    audio="$vctk_dir/wav48_silence_trimmed/${spkr}/${utt}_mic1.flac"
    if [ -f $audio ] && [ -f $txt ]; then
      echo $audio >> $audios
      # some transcripts (p376) have no line terminators:
      # this sed incantation adds them if missing
      cat $txt | sed -e '$a\' >> $transcripts
      printf "$audio $(cat $txt)\n" >> $meta
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
              s/ +/ /g;' \
  > ${transcripts}_clean

# Combine data into single file $workdir/vctk_meta_clean.txt
paste -d ' ' $audios ${transcripts}_clean > ${meta/.raw/.clean}
rm $audios $transcripts ${transcripts}_clean
