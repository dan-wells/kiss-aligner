#!/usr/bin/env python3

import argparse
import os
import re


def write_ctm(dirname, fname, lines):
    with open(os.path.join(dirname, fname), "w") as outf:
        outf.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split CTM files per utterance.")
    parser.add_argument("ctm_file", type=str,
        help="Input CTM file")
    parser.add_argument("split_ctm_dir", type=str,
        help="Output directory for split CTM files")
    parser.add_argument("--strip-pos", action="store_true",
        help="Strip word position markers from phone CTM entries")
    args = parser.parse_args()

    os.makedirs(args.split_ctm_dir, exist_ok=True)
    word_pos = re.compile(r"_(B|I|E|S) $")
    prev_utt = ""
    lines = []
    with open(args.ctm_file) as inf:
        for i, line in enumerate(inf):
            utt, *_ = line.split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                write_ctm(args.split_ctm_dir, prev_utt, lines)
                lines = []
            if args.strip_pos:
                line = re.sub(word_pos, "", line)
            lines.append(line)
            prev_utt = utt
        # final utt
        write_ctm(args.split_ctm_dir, prev_utt, lines)

