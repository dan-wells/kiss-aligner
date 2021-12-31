#!/usr/bin/env python3

import argparse
import os
import re


def load_ctm(ctm_file, strip_pos=False, sil_to_sp=False, sil_symbols=('SIL', 'SP')):
    """Read Kaldi CTM file and split to per-utterance alignments

    Args:
      ctm_file: Path to multi-utterance CTM file
      strip_pos: Flag to strip word-position labels from aligned symbols
      sil_to_sp: Convert silence symbols between words to short pauses (leading
        and trailing silences remain)
      sil_symbols: Pair of symbols to use for leading/trailing silence and
        short pauses respectively. Output will match exactly, input should use
        the same character sequences but can be different case

    Returns:
      utts: Dict mapping utterance IDs to string symbol sequences
    """
    word_pos = re.compile(r"_(B|E|I|S)$")
    sil, sp = sil_symbols
    sil_nocase = sil.lower()
    with open(ctm_file) as inf:
        prev_utt = ""
        utts = {}
        tokens = []
        for i, line in enumerate(inf):
            utt, conf, start, dur, token = line.strip().split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                utts[prev_utt] = tokens_to_text(tokens, sil_symbols)
                tokens = []
            if strip_pos:
                token = re.sub(word_pos, '', token)
            if sil_to_sp and token.lower() == sil_nocase:
                token = sp
            tokens.append(token)
            prev_utt = utt
        utts[prev_utt] = tokens_to_text(tokens, sil_symbols)
    return utts


def tokens_to_text(tokens, sil_symbols):
    """Convert token sequence to output string"""
    # undo leading/trailing sil_to_sp conversion
    tokens = fix_sil(tokens, sil_symbols)
    return ' '.join(tokens)


def fix_sil(tokens, sil_symbols):
    """Undo over-zealous silence symbol conversion while splitting CTM"""
    sil, sp = sil_symbols
    for i in [0, -1]:
        if tokens[i] == sp:
            tokens[i] = sil
    return tokens


def write_meta(utts, meta_out, sep=' ', audio_root=None):
    """Write output metadata file with utterance IDs and associated text

    Args:
      utts: Dict mapping utterance IDs to string symbol sequences
      meta_out: Path to write output file
      sep: Field separator to use in metadata output
      audio_root: If specified, convert utterance IDs (naively) to .wav
        filenames located under this directory
    """
    with open(meta_out, 'w') as outf:
        for utt, text in utts.items():
            if audio_root is not None:
                utt = os.path.join(audio_root, f"{utt}.wav")
            outf.write(f"{utt}{sep}{text}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Extract symbol sequences per utterance from CTM alignments",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('ctm_file', type=str,
        help="Path to Kaldi CTM file with alignments over all utterances")
    parser.add_argument('text_out', type=str,
        help="Path to write output file with utterance IDs and symbol sequences")
    parser.add_argument('--sep', type=str, default=' ',
        help="Field separator for output file")
    parser.add_argument('--strip-pos', action='store_true',
        help="Strip word position markers from phone CTM entries")
    parser.add_argument('--sil-to-sp', action='store_true',
        help="Convert inter-word silences to short pause symbol")
    parser.add_argument('--sil-symbols', type=str, nargs=2, default=['SIL', 'SP'],
        help="Symbols used for silence and short pauses")
    parser.add_argument('--audio-root', type=str, default=None,
        help="Convert utterance IDs to .wav filenames under this directory")
    args = parser.parse_args()

    utts = load_ctm(args.ctm_file, args.strip_pos, args.sil_to_sp, args.sil_symbols)
    write_meta(utts, args.text_out, args.sep, args.audio_root)
