#!/usr/bin/env python3

import glob
import os
import re
import sys
from itertools import zip_longest

_re_sentence_bound = re.compile(r'([.;:?!]”? )')

if __name__ == '__main__':
    _, src_txt_dir, out_txt_dir = sys.argv

    src_txts = sorted(glob.glob(os.path.join(src_txt_dir, '*.txt')))
    for src_txt in src_txts:
        utt_id, _ = os.path.splitext(os.path.basename(src_txt))
        out_txt = os.path.join(out_txt_dir, utt_id + '.txt')
        sent_id = 1
        with open(src_txt) as inf, open(out_txt, 'w') as outf:
            for line in inf:
                sents = re.split(_re_sentence_bound, line.strip())
                #for sent in sents:
                # preserve split delimiters for output text (?)
                for sent, delim in zip_longest(sents[::2], sents[1::2], fillvalue=''):
                    if sent:
                        #outf.write('{}_{:0>4} {}\n'.format(utt_id, sent_id, sent))
                        outf.write('{}_{:0>4} {}\n'.format(utt_id, sent_id, ''.join([sent, delim.strip()])))
                        sent_id += 1
