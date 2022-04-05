#!/usr/bin/env bash

# begin configuration section.
cmd=run.pl
frame_shift=10.0
#end configuration section.

echo "$0 $@"  # Print the command line for logging.

[ -f ./path.sh ] && . ./path.sh
. parse_options.sh || exit 1;

if [ $# -ne 3 ]; then
  echo "Usage: $0 [options] <lang-dir> <ali-dir|model-dir> <output-dir>"
  echo "Options:"
  echo "    --cmd (run.pl|queue.pl...)      # specify how to run the sub-processes."
  echo "    --frame-shift (default=10.0)    # specify this if your alignments have a frame-shift"
  echo "                                    # not equal to 10.0 milliseconds"
  echo "e.g.:"
  echo "$0 data/lang exp/tri3a_ali phone_state_ctm"
  echo "Produces per-utterance ctm in: phone_state_ctm/utt_id"
  exit 1;
fi

lang=$1
ali_dir=$2
ctm_dir=$3

model=$ali_dir/final.mdl

for f in $lang/words.txt $model $ali_dir/ali.1.gz; do
  [ ! -f $f ] && echo "$0: expecting file $f to exist" && exit 1;
done

nj=$(cat $ali_dir/num_jobs) || exit 1;

mkdir -p $ali_dir/log || exit 1;

# get pdf/state transition sequence per utterance
$cmd JOB=1:$nj $ali_dir/log/get_state_alignment.JOB.log \
  set -o pipefail '&&' convert-ali --reorder=false \
  $model $model $ali_dir/tree "ark:gunzip -c $ali_dir/ali.JOB.gz|" \
  ark,t:- \| gzip -c '>' $ali_dir/ali.trans.JOB.gz || exit 1

# get transition ids per phone pdf
show-transitions $lang/phones.txt $model $ali_dir/final.occs > $ali_dir/transitions

# write phone-state ctm files per utterance
python3 local/transitions_to_phone_ctm.py --nj $nj --frame-shift $frame_shift \
  $ali_dir/transitions $ali_dir $ctm_dir
