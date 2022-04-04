#!/usr/bin/env bash

GP=$SCRATCH_HOME/data/global_phone
GP_PL=$GP/Polish
DATA=$SCRATCH_HOME/data/global_phone/Polish/align/data/train
DICT=$SCRATCH_HOME/data/global_phone/Polish/align/data/local/dict

export LC_ALL=C
set -euo pipefail

type -p shorten >/dev/null || (echo "shorten not found, exiting"; exit 1)

mkdir -p $DATA
mkdir -p $DICT

# prepare data files
[ -f $DATA/text ] && rm $DATA/text
[ -f $DATA/wav.scp ] && rm $DATA/wav.scp
[ -f $DATA/utt2spk ] && rm $DATA/utt2spk
[ -f $DATA/spk2gender ] && rm $DATA/spk2gender

# TODO: ffmpeg can apparently read Shortened files (by .shn extension),
# but can't work out how to tell it that it's uncompressing to raw PCM.
# Might be nice to figure that out and put a pipe in wav.scp rather than
# converting all utterances to WAV here
printf "Processing data for speaker:\n"
for spkr_dir in $GP_PL/adc/*; do
  export spkr=PL${spkr_dir##*/}
  printf "  $spkr\n"
  mkdir -p $GP_PL/wav/$spkr
  for shn in $spkr_dir/*.shn; do
    utt=${shn%%.*}
    utt=${utt##*/}
    # decompress audio and add WAV headers
    wav=$GP_PL/wav/$spkr/${utt}.wav
    shorten -x $shn - | sox -t raw -r 16k -b 16 -e signed-integer --endian little - $wav
    # write data files
    printf "$utt $wav\n" >> $DATA/wav.scp
    printf "$utt $spkr\n" >> $DATA/utt2spk
  done
  # get text from per-speaker .trl files
  # need to strip punctuation but don't lowercase
  # text processing apparently left some BOM (u+FEFF) from source text inline
  # TODO: some additional punctuation it would be nice to filter out, but
  # can't figure out utf-8 in Perl... Most OOVs are proper nouns, so the
  # proportion of utts that would be saved by this is small
  perl -ne '
    chomp;
    my $spkr = $ENV{"spkr"};
    next if /SprecherID/;
    if ($_ =~ m/; (\d+):/) {
      my $utt = "${spkr}_$1";
      print "$utt ";
    } else {
      s/\xEF\xBB\xBF//g;
      s/[[:punct:]]/ /g;
      #s/([[:punct:]]|[–«»„“”])/ /g;
      #s/­/-/g;
      s/\s+/ /g;
      print "$_\n";
    }' $GP_PL/trl/${spkr}.trl >> $DATA/text
  # gender information not recorded for most speakers, so skip
  #mf=$(grep -Po ';SEX:\K((fe)?male)' $GP_PL/spk/${spkr}.spk)
  #printf "$spkr ${mf:0:1}\n" >> $DATA/spk2gender
done
utils/utt2spk_to_spk2utt.pl $DATA/utt2spk > $DATA/spk2utt
utils/fix_data_dir.sh $DATA

# prepare lexicon files
LEX=$GP/Dictionaries/PL/PolishGP.dict

# map phone set to common GlobalPhone symbols
python3 local/corpus/globalphone/prep_gp_lex.py \
  $LEX PL $DICT/lexicon.txt --phone_set gp

# extract phone symbols
cut -d' ' -f2- $DICT/lexicon.txt | \
  tr ' ' '\n' | grep -Pv '(^$|SIL)' | sort -u > $DICT/nonsilence_phones.txt

# add pronunciation for oov symbol
echo "<unk> SPN" >> $DICT/lexicon.txt

# create remaining files
echo "SIL" > $DICT/optional_silence.txt
printf "SIL\nSPN\n" > $DICT/silence_phones.txt
touch $DICT/extra_questions.txt
