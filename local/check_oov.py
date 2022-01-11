#!/usr/bin/env python3

import argparse
import locale
import os
import sys
from collections import defaultdict


def load_words(words_file):
    """Load vocabulary of words with known pronunciations

    Args:
      words_file: Path to Kaldi `words.txt` data file

    Returns:
      words: Set of known words
    """
    words = set()
    with open(words_file) as inf:
        for line in inf:
            words.add(line.strip().split()[0])
    return words


def check_oov(text_file, words):
    """Find utterances with out-of-vocabulary items in transcripts

    Args:
      text_file: Path to Kaldi `text` data file
      words: Set of known words

    Returns:
      oov_utts: Dict mapping utterance IDs to tuples like (transcript, oov_count),
        where transcripts have OOV items marked up: "this is an OOV_unknown word"
      oov_words: Dict mapping OOV words to count across transcripts
    """
    oov_utts = {}
    oov_words = defaultdict(int)
    with open(text_file) as inf:
        for line in inf:
            utt_id, *text = line.strip().split()
            oov_count = 0
            for i, word in enumerate(text):
                if word not in words:
                    oov_words[word] += 1
                    text[i] = "OOV_{}".format(word)
                    oov_count += 1
            if oov_count:
                oov_utts[utt_id] = (' '.join(text), oov_count)
    return oov_utts, dict(oov_words)


def write_oov_utts(oov_utts, outfile):
    """Write listing of utterances containing OOV items to file

    Args:
      oov_utts: Dict mapping utterance IDs to tuples like (transcript, oov_count),
        where transcripts have OOV items marked up: "this is an <UNKNOWN> word"
      outfile: Output file path
    """
    # sort as LC_ALL=C for compatibility with Kaldi sorting
    locale.setlocale(locale.LC_ALL, 'C')
    if oov_utts:
        with open(outfile, 'w') as outf:
            oov_total = 0
            for utt, (text, oov_count) in oov_utts.items():
                outf.write("{} {}\n".format(utt, text))
                oov_total += oov_count
        print("Found {} out-of-vocabulary items across {} utterances".format(
            oov_total, len(oov_utts)))


def write_oov_words(oov_words, outfile):
    """Write listing of OOV items to file

    Args:
      oov_words: Dict counting occurrences of OOV words
      outfile: Output file path
    """
    if oov_words:
        with open(outfile, 'w') as outf:
            for word, count in sorted(oov_words.items(),
                                      key=lambda x: x[1], reverse=True):
                outf.write("{} {}\n".format(word, count))
        print("Found {} unique out-of-vocabulary items".format(len(oov_words)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Check training transcripts for out-of-vocabulary items",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('words', type=str,
        help="Path to Kaldi `words.txt` data file listing words with known pronunciations")
    parser.add_argument('text', type=str,
        help="Path to Kaldi `text` data file listing training transcripts")
    parser.add_argument('--warn-on-oov', action='store_true',
        help="Return non-zero exit status if OOV items found")
    parser.add_argument('--workdir', type=str, default='align',
        help="Working directory for alignment")
    args = parser.parse_args()

    words = load_words(args.words)
    oov_utts, oov_words = check_oov(args.text, words)

    write_oov_utts(oov_utts, os.path.join(args.workdir, 'oov_utts.txt'))
    write_oov_words(oov_words, os.path.join(args.workdir, 'oov_words.txt'))

    # non-zero exit to abort aligner run
    if oov_words and args.warn_on_oov:
        sys.exit(1)
