#!/usr/bin/env bash

# Sample script to prepare `data/train/*` files for Kaldi alignment over VCTK v0.80 data

vctk_dir=$HOME/data/VCTK-Corpus
workdir=align

. ./path.sh
. utils/parse_options.sh

train=$workdir/data/train
mkdir -p $train

set -e

# Text transcripts are under VCTK-Corpus/txt
pushd $vctk_dir/txt >/dev/null
echo "Processing speaker utterances..."
for spkr in *; do 
  echo $spkr
  pushd $spkr >/dev/null
  for t in *.txt; do
    t=${t%.txt}
    # Basic text cleaning
    cat $t.txt \
      | sed -e '$a\' \
      | tr 'A-Z' 'a-z' \
      | perl -pe 's/\b[.,?!"]/ /g;
                  s/[.,?!"]\b/ /g;
                  s/ [.,?!"] / /g;
                  s/ [,.?!"]$//;
                  s/\)//g;
                  s/^ //g;
                  s/ +/ /g;' >> $workdir/transcripts
    echo $t >> $workdir/speakers
  done
  popd >/dev/null
done
popd >/dev/null

# Combine utterance IDs and cleaned transcripts
paste -d' ' $workdir/speakers $workdir/transcripts | sort > $train/text

[ -f $train/wav.scp ] && rm $train/wav.scp
[ -f $train/utt2spk ] && rm $train/utt2spk
while read utt; do
  # Write wav.scp with sox pipe to downsample audio to 16 kHz
  printf "${utt} sox -G $vctk_dir/wav48/${utt%_*}/${utt}.wav -r 16k -t wav - |\n" \
    >> $train/wav.scp
  # Write utt2spk
  printf "${utt} ${utt%_*}\n" >> $train/utt2spk
done < <(sort $workdir/speakers)

# Generate spk2utt from utt2spk
utils/utt2spk_to_spk2utt.pl $train/utt2spk > $train/spk2utt

# Delete temporary files
rm $workdir/{speakers,transcripts}
