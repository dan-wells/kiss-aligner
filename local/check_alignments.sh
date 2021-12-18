#!/usr/bin/env bash

ali_dir=$1
workdir=$2

# Surface some useful statistics
echo "At utterance \(begin\|end\), \(SIL\|nonsilence\) accounts
The optional-silence phone
Assuming 100 frames per second
Utterance-internal optional-silences" | grep -f - $ali_dir/log/analyze_alignments.log | sed 's/, with duration.*//'

# Check for retried and failed alignments
retried=$workdir/retried_alignment.txt
failed=$workdir/failed_to_align.txt

grep -h "WARNING" $ali_dir/log/align_pass2.*.log > $workdir/warnings
grep -Po "Retrying utterance \K.+ (?=with)" $workdir/warnings > $workdir/retried_utts
grep -Po "Did not successfully decode file \K.+(?=,)" $workdir/warnings > $workdir/failed_utts

grep -f $workdir/failed_utts -v $workdir/retried_utts | grep -f - $workdir/data/train/text > $retried
grep -f $workdir/failed_utts $workdir/data/train/text > $failed

echo "Aligned $(cat $retried | wc -l) utterances on second attempt using wider beam"
echo "Failed to align $(cat $failed | wc -l) utterances"

rm $workdir/{warnings,failed_utts,retried_utts}
