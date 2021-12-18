#!/usr/bin/env bash

# Sample script to prepare `data/lang/*` files for cmudict lexicon

workdir=align

. ./path.sh
. utils/parse_options.sh

dict=$workdir/data/local/dict
mkdir -p $dict

set -e 

# Download cmudict
if [ ! -f $dict/cmudict.dict ]; then
  wget -O $dict/cmudict.dict \
    "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
fi

# Strip annotations for pronunciation variants and stress markers,
# and remove duplicate entries
perl -pe 's/\(\d+\)//; s/[012]//g; s/ #.*$//;' $dict/cmudict.dict \
  | sort -u > $dict/lexicon.txt

# Extract phone symbols from lexicon
cut -d' ' -f2- $dict/lexicon.txt \
  | tr ' ' '\n' | sort -u > $dict/nonsilence_phones.txt

# Add pronunciation for OOV symbol
echo "<unk> SPN" >> $dict/lexicon.txt

# Create remaining files
echo "SIL" > $dict/optional_silence.txt
printf "SIL\nSPN\n" > $dict/silence_phones.txt
touch $dict/extra_questions.txt
