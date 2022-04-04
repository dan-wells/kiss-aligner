#!/usr/bin/env python3

import argparse
import os
import re


def split_ctm(ctm_file, split_ctm_dir, strip_pos=False, enc='utf-8'):
    """Split Kaldi CTM file per utterance and write to directory"""
    os.makedirs(split_ctm_dir, exist_ok=True)
    word_pos = re.compile(r'_(B|I|E|S) $')
    prev_utt = ''
    lines = []
    with open(ctm_file, encoding=enc) as inf:
        for i, line in enumerate(inf):
            utt, *_ = line.split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                write_ctm(split_ctm_dir, prev_utt, lines)
                lines = []
            if strip_pos:
                line = re.sub(word_pos, '', line)
            lines.append(line)
            prev_utt = utt
        # final utt
        write_ctm(split_ctm_dir, prev_utt, lines, enc)


def write_ctm(dirname, fname, lines, enc='utf-8'):
    with open(os.path.join(dirname, fname), "w", encoding=enc) as outf:
        outf.writelines(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split CTM files per utterance.")
    parser.add_argument('ctm_file', type=str,
        help="Input CTM file")
    parser.add_argument('split_ctm_dir', type=str,
        help="Output directory for split CTM files")
    parser.add_argument('--strip-pos', action='store_true',
        help="Strip word position markers from phone CTM entries")
    parser.add_argument('--file-enc', type=str, default='utf-8',
        help="File encoding for input/output text")
    args = parser.parse_args()

    split_ctm(args.ctm_file, args.split_ctm_dir, args.strip_pos, args.file_enc)

