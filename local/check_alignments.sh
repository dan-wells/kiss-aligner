#!/usr/bin/env bash

ali=$1
workdir=$2
data=$3

# Surface some useful statistics
echo "At utterance \(begin\|end\), \(SIL\|nonsilence\) accounts
The optional-silence phone
Assuming 100 frames per second
Utterance-internal optional-silences" | grep -f - $ali/log/analyze_alignments.log | sed 's/, with duration.*//'

# Check for retried and failed alignments
retried=$workdir/retried_alignment.txt
failed=$workdir/failed_to_align.txt

grep -h "WARNING" $ali/log/align_pass2.*.log > $workdir/warnings
grep -Po "Retrying utterance \K.+ (?=with)" $workdir/warnings > $workdir/retried_utts
grep -Po "Did not successfully decode file \K.+(?=,)" $workdir/warnings > $workdir/failed_utts

grep -f $workdir/failed_utts -v $workdir/retried_utts | grep -f - $data/text > $retried
num_retried=$(cat $retried | wc -l)
if [ $num_retried -gt 0 ]; then
  echo "Aligned $num_retried utterances on second attempt using wider beam: $retried"
else
  rm $retried
fi

grep -f $workdir/failed_utts $data/text > $failed
num_failed=$(cat $failed | wc -l)
if [ $num_failed -gt 0 ]; then
  echo "Failed to align $num_failed utterances: $failed"
else
  rm $failed
fi

rm $workdir/{warnings,failed_utts,retried_utts}
