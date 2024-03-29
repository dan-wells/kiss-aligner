#!/usr/bin/env python3

import argparse
import os
import re

import tgt
from tgt.core import TextGrid, IntervalTier, Interval


def load_ctm(ctm_file, enc='utf-8'):
    """Read Kaldi CTM file and split to per-utterance alignments

    Args:
      ctm_file: Path to multi-utterance CTM file

    Returns:
      utts: Dict mapping utterance IDs to alignments represented as lists of
        (token, start_time, duration) tuples
    """
    with open(ctm_file, encoding=enc) as inf:
        prev_utt = ""
        utts = {}
        tokens = []
        for i, line in enumerate(inf):
            utt, conf, start, dur, token = line.strip().split()
            if i == 0:
                prev_utt = utt
            if prev_utt != utt:
                utts[prev_utt] = tokens
                tokens = []
            tokens.append((token, float(start), float(dur)))
            prev_utt = utt
        utts[prev_utt] = tokens
    return utts


def load_ctm_with_punc(ctm_file, enc='utf-8'):
    """Read Kaldi CTM file with punctuation and split to per-utterance alignments

    Meant for phone CTM with punctuation symbols using PUNC phone (therefore
    transcribed as standalone words like PUNC_S). Punctuation intervals are
    merged with any surrounding silences, assuming this is how we want them to
    be pronounced.

    Args:
      ctm_file: Path to multi-utterance CTM file

    Returns:
      utts: Dict mapping utterance IDs to alignments represented as lists of
        (token, start_time, duration) tuples
    """
    with open(ctm_file, encoding=enc) as inf:
        prev_utt = ""
        prev_token = ""
        prev_start = 0
        tmp_dur = 0
        utts = {}
        tokens = []
        for i, line in enumerate(inf):
            utt, conf, start, dur, token = line.strip().split()
            start = float(start)
            dur = float(dur)
            if i == 0:
                prev_utt = utt
            # TODO: if there are multiple PUNC, this merges all into the first
            if prev_utt != utt:
                if prev_token in ["SIL", "PUNC_S"]:
                    tokens.append((prev_token, prev_start, tmp_dur))
                utts[prev_utt] = tokens
                tokens = []
                prev_token = ""
                tmp_dur = 0
            if prev_token in ["SIL", "PUNC_S"]:
                if token in ["SIL", "PUNC_S"]:
                    tmp_dur += dur
                    prev_token = "PUNC_S"  # keep PUNC always (never two SIL in a row)
                    prev_utt = utt
                    continue
                else:
                    # moved past SIL/PUNC block
                    tokens.append((prev_token, float(start) - tmp_dur, tmp_dur))
                    tmp_dur = 0
            if (token in ["SIL", "PUNC_S"]) and (prev_token not in ["SIL", "PUNC_S"]):
                tmp_dur = float(dur)
                prev_token = token
                prev_utt = utt
                prev_start = start
                continue
            tokens.append((token, float(start), float(dur)))
            prev_utt = utt
            prev_token = token
        utts[prev_utt] = tokens
    return utts


def load_utt2dur(utt2dur_file):
    """Load utterance durations from Kaldi utt2dur file

    Args:
      utt2dur_file: Path to utt2dur file

    Returns:
      utt2dur: Dict mapping utterance IDs to durations in seconds (float)
    """
    utt2dur = {}
    with open(utt2dur_file) as inf:
        for line in inf:
            utt, dur = line.strip().split()
            utt2dur[utt] = float(dur)
    return utt2dur


def make_tier(tier_name, alignment, utt_start, utt_end, sil, strip_pos, punc_tier=None):
    """Create TextGrid interval tier from aligned tokens

    Args:
      tier_name: Label to use for individual tier in final TextGrid
      alignment: List of (token, start_time, duration) tuples
      utt_start: Time index of utterance start, in seconds
      utt_end: Time index of utterance end, in seconds
      sil: Symbol used for optional silence tokens
      strip_pos: Flag to strip word-position labels from aligned symbols
      punc_tier: tgt.core.IntervalTier to extract original punctuation symbols
        for PUNC phone intervals

    Returns:
      tier: tgt.core.IntervalTier object representing aligned tokens
    """
    # pattern to strip Kaldi markers for phone position within words
    word_pos = re.compile(r"_(B|E|I|S)$")

    tier = IntervalTier(utt_start, utt_end, tier_name)
    n_tokens = len(alignment)
    intervals = []
    for i, token in enumerate(alignment):
        text, start, dur = token
        # words: <eps>, phones: SIL (default)
        if text == sil:
            if (i == 0) or (i == n_tokens - 1):
                # leading/trailing silence around utterance
                text = 'sil'
            else:
                # short pause between words
                text = 'sp'
        if i == n_tokens - 1:
            # use full duration from utt2dur here so we don't lose any time
            # to Kaldi's frame shift
            end = utt_end
        else:
            # ms precision
            start = round(start, 3)
            end = round(start + dur, 3)
        if punc_tier is not None and text == 'PUNC_S':
            punc_ints = punc_tier.get_annotations_between_timepoints(start, end)
            for punc_int in punc_ints:
                text = punc_int.text
                if text not in ["sil", "sp"]:
                    break  # keep PUNC text only, merge with silence intervals
        if tier_name == 'phones' and strip_pos:
            text = re.sub(word_pos, '', text)
        intervals.append(Interval(start, end, text))
    tier.add_intervals(intervals)
    return tier


def write_textgrids(utts_word, utts_phone, utt2dur, tg_dir, sil_phone='SIL', strip_pos=False, punc=False):
    """Write TextGrid files with word- and phone-level alignments per utterance 

    Args:
      utts_word: Dict mapping utterance IDs to word-level alignments stored as
        lists of (token, start_time, duration) tuples
      utts_phone: Dict mapping utterance IDs to phone-level alignments
      utt2dur: Dict mapping utterance IDs to durations
      tg_dir: Directory to write TextGrid files per utterance
      sil_phone: Phone symbol used for optional silence
      strip_pos: Flag to strip word-position labels from aligned symbols
    """
    num_utts = len(utts_phone)
    assert len(utts_word) == num_utts
    for i, utt in enumerate(utts_phone, 1):
        utt_start = 0
        utt_end = utt2dur[utt]
        # nb. we do nothing about OOV items here -- they will be marked by
        # whatever symbols Kaldi knows about, e.g. <unk> in words tier and
        # SPN in phones tier
        tgf = os.path.join(tg_dir, f"{utt}.TextGrid")
        textgrid = TextGrid(tgf)
        word_tier = make_tier("words", utts_word[utt], utt_start, utt_end, '<eps>', strip_pos)
        textgrid.add_tier(word_tier)
        if punc:
            phone_tier = make_tier("phones", utts_phone[utt], utt_start, utt_end, sil_phone, strip_pos, word_tier)
        else:
            phone_tier = make_tier("phones", utts_phone[utt], utt_start, utt_end, sil_phone, strip_pos)
        textgrid.add_tier(phone_tier)
        tgt.io.write_to_file(textgrid, tgf, format="long")

        # progress bar
        log_line_end = '\n' if i == num_utts else '\r'
        n_done = int(i / num_utts * 40)
        print("Creating TextGrids [{}{}] {}/{}".format(
              n_done * '#', (40 - n_done) * '-', i, num_utts),
              end=log_line_end)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert CTM alignments to Praat TextGrid format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('word_ctm', type=str,
        help="Path to word-level alignments in Kaldi CTM format")
    parser.add_argument('phone_ctm', type=str,
        help="Path to phone-level alignments in Kaldi CTM format")
    parser.add_argument('tg_dir', type=str,
        help="Directory to write TextGrid files per utterance")
    parser.add_argument('--sil', type=str, default='SIL',
        help="Optional silence phone symbol")
    parser.add_argument('--punc', action='store_true',
        help="Handle punctuation symbols aligned as silence")
    parser.add_argument('--strip-pos', action='store_true',
        help="Strip word position markers from phone CTM entries")
    parser.add_argument('--datadir', type=str, default='./align/data/train',
        help="Directory containing data to be aligned")
    parser.add_argument('--file-enc', type=str, default='utf-8',
        help="File encoding for input/output text")
    args = parser.parse_args()


    utts_word = load_ctm(args.word_ctm, args.file_enc)
    if args.punc:
        utts_phone = load_ctm_with_punc(args.phone_ctm)
    else:
        utts_phone = load_ctm(args.phone_ctm)
    utt2dur = load_utt2dur(os.path.join(args.datadir, 'utt2dur'))

    os.makedirs(args.tg_dir, exist_ok=True)
    write_textgrids(utts_word, utts_phone, utt2dur, args.tg_dir, args.sil, args.strip_pos, args.punc)
