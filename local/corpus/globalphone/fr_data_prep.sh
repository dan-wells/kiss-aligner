#!/usr/bin/env bash

GP=$SCRATCH_HOME/data/global_phone
GP_FR=$GP/French
DATA=$SCRATCH_HOME/data/global_phone/French/align/data/train
DICT=$SCRATCH_HOME/data/global_phone/French/align/data/local/dict

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
for spkr_dir in $GP_FR/adc/*; do
  export spkr=FR${spkr_dir##*/}
  printf "  $spkr\n"
  mkdir -p $GP_FR/wav/$spkr
  for shn in $spkr_dir/*; do
    utt=${shn%%.*}
    utt=${utt##*/}
    # decompress audio and add WAV headers
    wav=$GP_FR/wav/$spkr/${utt}.wav
    shorten -x $shn - | sox -t raw -r 16k -b 16 -e signed-integer --endian little - $wav
    # write data files
    printf "$utt $wav\n" >> $DATA/wav.scp
    printf "$utt $spkr\n" >> $DATA/utt2spk
  done
  # get text from re-encoded per-speaker .trl files
  # need to lowercase and remove all punctuation to match lexicon
  iconv -f ISO-8859-1 -t UTF-8 $GP_FR/trl/${spkr}.trl | \
    perl -ne '
     chomp;
     my $spkr = $ENV{"spkr"};
     next if /SprecherID/;
     if ($_ =~ m/; (\d+):/) {
       my $utt = "${spkr}_$1";
       print "$utt ";
     } else {
       s/[[:punct:]]/ /g;
       s/\s+/ /g;
       my $text = lc $_;
       print "$text\n";
     }
  ' >> $DATA/text
  # get gender information per speaker
  mf=$(grep -Po ';SEX:\K((fe)?male)' $GP_FR/spk/${spkr}.spk)
  printf "$spkr ${mf:0:1}\n" >> $DATA/spk2gender
done
utils/utt2spk_to_spk2utt.pl $DATA/utt2spk > $DATA/spk2utt
utils/fix_data_dir.sh $DATA

# prepare lexicon files
LEX=$GP/Dictionaries/FR/French-GPDict.txt

# map phone set to common GlobalPhone symbols
python3 local/corpus/globalphone/prep_gp_lex.py \
  $LEX FR $DICT/lexicon.txt --phone_set gp

# extract phone symbols
cut -d' ' -f2- $DICT/lexicon.txt | \
  tr ' ' '\n' | grep -v '^$' | sort -u > $DICT/nonsilence_phones.txt

# make sure we have appropriate entries for various elided forms
# e.g. article l' (again using mapped GlobalPhone symbols)
echo "l l
d d
c s
s s
n n
j Z
t t
m m" >> $DICT/lexicon.txt
# add pronunciation for oov symbol
echo "<unk> SPN" >> $DICT/lexicon.txt

# create remaining files
echo "SIL" > $DICT/optional_silence.txt
printf "SIL\nSPN\n" > $DICT/silence_phones.txt
touch $DICT/extra_questions.txt
