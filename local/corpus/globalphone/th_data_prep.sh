#!/usr/bin/env bash

GP=$SCRATCH_HOME/data/global_phone
GP_TH=$GP/Thai
DATA=$GP_TH/align/data/train
DICT=$GP_TH/align/data/local/dict

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
for spkr_dir in $GP_TH/adc/*; do
  export spkr=TH${spkr_dir##*/}
  printf "  $spkr\n"
  mkdir -p $GP_TH/wav/$spkr
  for shn in $spkr_dir/*; do
    utt=${shn%%.*}
    utt=${utt##*/}
    # decompress audio and add WAV headers
    wav=$GP_TH/wav/$spkr/${utt}.wav
    shorten -x $shn - | sox -t raw -r 16k -b 16 -e signed-integer --endian little - $wav
    # write data files
    printf "$utt $wav\n" >> $DATA/wav.scp
    printf "$utt $spkr\n" >> $DATA/utt2spk
  done
  # get text from per-speaker .trl files
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
  ' $GP/Dictionaries/TH/trl-segmented/${spkr}.trl >> $DATA/text
  # get gender information per speaker
  #mf=$(grep -Po ';SEX:\K((fe)?male)' $GP_TH/spk/${spkr}.spk)
  #printf "$spkr ${mf:0:1}\n" >> $DATA/spk2gender
done
utils/utt2spk_to_spk2utt.pl $DATA/utt2spk > $DATA/spk2utt
utils/fix_data_dir.sh $DATA

# prepare lexicon files -- with and without tone
LEX=$GP/Dictionaries/TH/Thai-GPDict.25k
LEX_TONE=$GP/Dictionaries/TH/Thai-GPDict.12k.tones

# not mapping phone set to unified GlobalPhone here -- want to
# maintain tone markers without worrying about expanding diphthongs.
# where we have a tone-marked entry, use that
python3 -c "
from local.corpus.globalphone.globalphone import GlobalPhoneLex
th_tone_lex = GlobalPhoneLex('$LEX_TONE', 'TH', map_ipa=False)
th_lex = GlobalPhoneLex('$LEX', 'TH', map_ipa=False)
for key, pron in th_lex.lex.items():
    if key not in th_tone_lex.lex:
        th_tone_lex.lex[key] = pron
th_tone_lex.write_lex('$DICT/lexicon.txt')
"

# extract phone symbols
cut -d' ' -f2- $DICT/lexicon.txt | \
  tr ' ' '\n' | grep -Pv '(^$|SIL)' | sort -u > $DICT/nonsilence_phones.txt

# add pronunciation for oov symbol
echo "<unk> SPN" >> $DICT/lexicon.txt

# create remaining files
echo "SIL" > $DICT/optional_silence.txt
printf "SIL\nSPN\n" > $DICT/silence_phones.txt

# account for tone variants in alignment
[ -f $DICT/extra_questions.txt ] && rm $DICT/extra_questions.txt
for v in a{,a} e{,e} i{,i,ia} o{,o} q{,q} u{,u,ua} v{,v,va} x{,x} y{,y}; do
  printf "$v " >> $DICT/extra_questions.txt
  for t in {0..4}; do
    printf "$v$t " >> $DICT/extra_questions.txt
  done
  printf "\n" >> $DICT/extra_questions.txt
done
