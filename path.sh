export KALDI_ROOT=$HOME/kaldi

# Set up local symlinks to Kaldi script utilities
[ ! -L steps ] && ln -s $KALDI_ROOT/egs/wsj/s5/steps steps
[ ! -L utils ] && ln -s $KALDI_ROOT/egs/wsj/s5/utils utils

# Configure path for Kaldi binaries
[ -f $KALDI_ROOT/tools/env.sh ] && . $KALDI_ROOT/tools/env.sh
export PATH=$PWD/utils:$KALDI_ROOT/tools/openfst/bin:$PWD:$PATH
[ ! -f $KALDI_ROOT/tools/config/common_path.sh ] && echo >&2 "The standard file $KALDI_ROOT/tools/config/common_path.sh is not present -> Exit!" && exit 1
. $KALDI_ROOT/tools/config/common_path.sh

# Ensure consistent sorting of data files
export LC_ALL=C
