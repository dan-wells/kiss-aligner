#!/usr/bin/env bash

GP=$SCRATCH_HOME/data/global_phone
GP_HA=$GP/Hausa/Hausa/Data
DATA=$GP_HA/align/data/train
DICT=$GP_HA/align/data/local/dict

export LC_ALL=C
set -euo pipefail

mkdir -p $DATA
mkdir -p $DICT

# prepare data files
[ -f $DATA/text ] && rm $DATA/text
[ -f $DATA/wav.scp ] && rm $DATA/wav.scp
[ -f $DATA/utt2spk ] && rm $DATA/utt2spk
[ -f $DATA/spk2gender ] && rm $DATA/spk2gender

printf "Processing data for speaker:\n"
for spkr_dir in $GP_HA/adc/*; do
  export spkr=HA${spkr_dir##*/}
  printf "  $spkr\n"
  mkdir -p $GP_HA/wav/$spkr
  for adc in $spkr_dir/*.adc; do
    utt=${adc%%.*}
    utt=${utt##*/}
    # add WAV headers to audio (this data is not shortened)
    wav=$GP_HA/wav/$spkr/${utt}.wav
    sox -t raw -r 16k -b 16 -e signed-integer --endian little $adc $wav
    # write data files
    printf "$utt $wav\n" >> $DATA/wav.scp
    printf "$utt $spkr\n" >> $DATA/utt2spk
  done
  # get text from re-encoded per-speaker .trl files
  iconv -f ASCII -t UTF-8 $GP_HA/trl/${spkr}.trl | \
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
  # get gender information per speaker (fixed HA0{16,71}.spk)
  mf=$(grep -Po ';SEX:\K((fe)?male)' $GP_HA/spk/${spkr}.spk)
  printf "$spkr ${mf:0:1}\n" >> $DATA/spk2gender
done
utils/utt2spk_to_spk2utt.pl $DATA/utt2spk > $DATA/spk2utt
utils/fix_data_dir.sh $DATA

# prepare lexicon files
LEX=$GP/Dictionaries/HA/Hausa-GPDict.txt

# not mapping phone set to unified GlobalPhone here -- want to
# maintain tone markers without worrying about expanding diphthongs
python3 local/corpus/globalphone/prep_gp_lex.py \
  $LEX HA $DICT/lexicon.txt --keep-tone --keep-length

# note: _S is reserved for some uses of silence phones, so we
# convert the short length tag to _Sh
sed -i 's/_S/_Sh/g' $DICT/lexicon.txt

# extract phone symbols
cut -d' ' -f2- $DICT/lexicon.txt | \
  tr ' ' '\n' | grep -Pv '(^$|SIL)' | sort -u > $DICT/nonsilence_phones.txt
# add some phones which don't occur in the lexicon
echo "e_T3
o_T3
u_T3" >> $DICT/nonsilence_phones.txt

# add pronunciation for oov symbol
echo "<unk> SPN" >> $DICT/lexicon.txt

# create remaining files
echo "SIL" > $DICT/optional_silence.txt
printf "SIL\nSPN\n" > $DICT/silence_phones.txt

# account for tone and length variants in alignment
# note: only one of tone or length is ever marked, which seems
# like a mistake but nothing to do about it
[ -f $DICT/extra_questions.txt ] && rm $DICT/extra_questions.txt
for v in a e i o u; do
  printf "$v " >> $DICT/extra_questions.txt
  for t in _{L,Sh,T1,T2,T3}; do
    printf "$v$t " >> $DICT/extra_questions.txt
  done
  printf "\n" >> $DICT/extra_questions.txt
done
