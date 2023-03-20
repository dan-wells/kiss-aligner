#!/bin/sh

out_dir=segment_utts/data/long
text_raw=$out_dir/text_long_raw
text_clean=$out_dir/text

mkdir -p $out_dir
rm $text_raw
rm $text_clean

for txt in txt/*; do
  utt=${txt#txt/}
  utt=${utt%.txt}
  oneline=$(paste -sd' ' $txt)
  echo "$utt $oneline" >> $text_raw
done

python normalize_text.py $text_raw $text_clean
