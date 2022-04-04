#!/usr/bin/env bash

GP=$SCRATCH_HOME/data/global_phone
GP_MA=$GP/Mandarin
DATA=$SCRATCH_HOME/data/global_phone/Mandarin/align/data/train
DICT=$SCRATCH_HOME/data/global_phone/Mandarin/align/data/local/dict

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
for spkr_dir in $GP_MA/adc/*; do
  export spkr=MA${spkr_dir##*/}
  printf "  $spkr\n"
  mkdir -p $GP_MA/wav/$spkr
  for shn in $spkr_dir/*; do
    utt=${shn%%.*}
    utt=${utt##*/}
    # fix different language code between lexicon and data
    utt=${utt/CH/MA}
    # decompress audio and add WAV headers
    wav=$GP_MA/wav/$spkr/${utt}.wav
    shorten -x $shn - | sox -t raw -r 16k -b 16 -e signed-integer --endian little - $wav
    # write data files
    printf "$utt $wav\n" >> $DATA/wav.scp
    printf "$utt $spkr\n" >> $DATA/utt2spk
  done
  # get text from re-encoded per-speaker .rmn files
  iconv -f ASCII -t UTF-8 $GP_MA/rmn/${spkr/MA/CH}.rmn | \
    perl -ne '
     chomp;
     my $spkr = $ENV{"spkr"};
     next if /SprecherID/;
     if ($_ =~ m/; (\d+):/) {
       my $utt = "${spkr}_$1";
       print "$utt ";
     } else {
       print "$_\n";
     }
  ' >> $DATA/text
  # get gender information per speaker
  mf=$(grep -Po ';SEX:\K((fe)?male)' $GP_MA/spk/${spkr/MA/CH}.spk)
  printf "$spkr ${mf:0:1}\n" >> $DATA/spk2gender
done
utils/utt2spk_to_spk2utt.pl $DATA/utt2spk > $DATA/spk2utt
utils/fix_data_dir.sh $DATA

# prepare lexicon files
LEX=$GP/Dictionaries/MA/Mandarin-GPDict.txt

# not mapping phone set to unified GlobalPhone here -- want to
# maintain tone markers without worrying about expanding diphthongs
python3 local/corpus/globalphone/prep_gp_lex.py \
  $LEX MA $DICT/lexicon.txt

# extract phone symbols
cut -d' ' -f2- $DICT/lexicon.txt | \
  tr ' ' '\n' | grep -Pv '(^$|SIL)' | sort -u > $DICT/nonsilence_phones.txt
# add some phones which don't occur in the lexicon
echo "iou5
va5
ve5" >> $DICT/nonsilence_phones.txt

# add pronunciation for oov symbol
echo "<unk> SPN" >> $DICT/lexicon.txt

# create remaining files
echo "SIL" > $DICT/optional_silence.txt
printf "SIL\nSPN\n" > $DICT/silence_phones.txt

# account for tone variants in alignment
[ -f $DICT/extra_questions.txt ] && rm $DICT/extra_questions.txt
for t in {1..5}; do
  for v in a{,i,o} e{,i} i{,a,ao,e,i,o,ou,u} o{,u} u{,a,ai,e,ei,o} v{,a,e}; do
    printf "$v$t " >> $DICT/extra_questions.txt
  done
  printf "\n" >> $DICT/extra_questions.txt
done
