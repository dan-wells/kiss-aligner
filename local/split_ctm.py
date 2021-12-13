#!/usr/bin/env python3

import os
import sys


def load_ctm(ctm_file):
    with open(ctm_file) as inf:
        prev_utt = ""
        utts = {}
        syms = []
        for i, line in enumerate(inf):
            utt, conf, start, dur, sym = line.strip().split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                utts[prev_utt] = syms
                syms = []
            syms.append((sym, float(start), float(dur)))
            prev_utt = utt
        utts[prev_utt] = syms
    return utts


if __name__ == "__main__":
    try:
        _, ctm_file, split_ctm_dir = sys.argv
    except ValueError:
        print("Usage: python split_ctm.py ctm_file split_ctm_dir")
        sys.exit(1)

    os.makedirs(split_ctm_dir, exist_ok=True)

    with open(ctm_file) as inf:
        prev_utt = ""
        lines = []
        for i, line in enumerate(inf):
            utt, *_ = line.split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                with open(os.path.join(split_ctm_dir, prev_utt), "w") as outf:
                    outf.writelines(lines)
                lines = []
            lines.append(line)
            prev_utt = utt
        with open(os.path.join(split_ctm_dir, prev_utt), "w") as outf:
            outf.writelines(lines)
