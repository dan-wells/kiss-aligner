#!/usr/bin/env bash

# Sample script to clean up cmudict lexicon

workdir=align

. ./path.sh
. utils/parse_options.sh

mkdir -p $workdir

set -e 

# Download cmudict
if [ ! -f $workdir/cmudict.dict ]; then
  wget -O $workdir/cmudict.raw.dict \
    "https://raw.githubusercontent.com/cmusphinx/cmudict/master/cmudict.dict"
fi

# Strip annotations for pronunciation variants and stress markers,
# and remove duplicate entries
perl -pe 's/\(\d+\)//; s/[012]//g; s/ #.*$//;' $workdir/cmudict.raw.dict \
  | sort -u > $workdir/cmudict.clean.dict
