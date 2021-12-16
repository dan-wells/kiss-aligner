#!/usr/bin/env bash

# begin configuration section.
cmd=run.pl
frame_shift=0.01
#end configuration section.

echo "$0 $@"  # Print the command line for logging.

[ -f ./path.sh ] && . ./path.sh
. parse_options.sh || exit 1;

if [ $# -ne 2 ] && [ $# -ne 3 ]; then
  echo "Usage: $0 [options] <lang-dir> <ali-dir|model-dir> [<output-dir>]"
  echo "(<output-dir> defaults to  <ali-dir|model-dir>.)"
  echo " Options:"
  echo "    --cmd (run.pl|queue.pl...)      # specify how to run the sub-processes."
  echo "    --frame-shift (default=0.01)    # specify this if your alignments have a frame-shift"
  echo "                                    # not equal to 0.01 seconds"
  echo "e.g.:"
  echo "$0 data/lang exp/tri3a_ali"
  echo "Produces ctm in: exp/tri3a_ali/ctm.phone"
  exit 1;
fi

lang=$1
ali_dir=$2
dir=$3
if [ -z $dir ]; then
  dir=$ali_dir
fi

model=$ali_dir/final.mdl

for f in $lang/words.txt $model $ali_dir/ali.1.gz; do
  [ ! -f $f ] && echo "$0: expecting file $f to exist" && exit 1;
done

nj=`cat $ali_dir/num_jobs` || exit 1;

mkdir -p $dir/log || exit 1;

$cmd JOB=1:$nj $dir/log/get_phone_ctm.JOB.log \
  set -o pipefail '&&' ali-to-phones --frame-shift=$frame_shift \
  --ctm-output $model "ark:gunzip -c $ali_dir/ali.JOB.gz|" - \| \
  utils/int2sym.pl -f 5 $lang/phones.txt \| \
  gzip -c '>' $dir/ctm.phone.JOB.gz || exit 1

for n in `seq $nj`; do 
  gunzip -c $dir/ctm.phone.$n.gz
done > $dir/ctm.phone || exit 1;
rm $dir/ctm.phone.*.gz
