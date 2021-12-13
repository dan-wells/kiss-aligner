# Configure path for Kaldi binaries
export KALDI_ROOT=$HOME/tools/kaldi
[ -f $KALDI_ROOT/tools/env.sh ] && . $KALDI_ROOT/tools/env.sh
export PATH=$KALDI_ROOT/tools/openfst/bin:$PWD:$PATH
[ ! -f $KALDI_ROOT/tools/config/common_path.sh ] && echo >&2 "The standard file $KALDI_ROOT/tools/config/common_path.sh is not present -> Exit!" && exit 1
. $KALDI_ROOT/tools/config/common_path.sh

# Set up local symlinks to Kaldi script utilities
[ ! -L steps ] && ln -s $KALDI_ROOT/egs/wsj/s5/steps steps
[ ! -L utils ] && ln -s $KALDI_ROOT/egs/wsj/s5/utils utils

# Ensure consistent sorting of data files
export LC_ALL=C
