#!/usr/bin/env python3

import argparse
import os
import re

import tgt
from tgt.core import TextGrid, IntervalTier, Interval


def load_ctm(ctm_file):
    """Read Kaldi CTM file and split to per-utterance alignments

    Args:
      ctm_file: Path to multi-utterance CTM file

    Returns:
      utts: Dict mapping utterance IDs to alignments represented as lists of
        (token, start_time, duration) tuples
    """
    with open(ctm_file) as inf:
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


def make_tier(tier_name, alignment, utt_start, utt_end, sil):
    """Create TextGrid interval tier from aligned tokens

    Args:
      tier_name: Label to use for individual tier in final TextGrid
      alignment: List of (token, start_time, duration) tuples
      utt_start: Time index of utterance start, in seconds
      utt_end: Time index of utterance end, in seconds
      sil: Symbol used for optional silence tokens

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
            end = round(start + dur, 2)
        if tier_name == 'phones':
            text = re.sub(word_pos, '', text)
        intervals.append(Interval(start, end, text))
    tier.add_intervals(intervals)
    return tier


def write_textgrids(utts_word, utts_phone, utt2dur, tg_dir, sil_phone='SIL'):
    """Write TextGrid files with word- and phone-level alignments per utterance 

    Args:
      utts_word: Dict mapping utterance IDs to word-level alignments stored as
        lists of (token, start_time, duration) tuples
      utts_phone: Dict mapping utterance IDs to phone-level alignments
      utt2dur: Dict mapping utterance IDs to durations
      tg_dir: Directory to write TextGrid files per utterance
      sil_phone: Phone symbol used for optional silence
    """
    num_utts = len(utts_phone)
    assert len(utts_word) == num_utts
    log_interval = int(num_utts / 20) + 1
    for i, utt in enumerate(utts_phone, 1):
        utt_start = 0
        utt_end = utt2dur[utt]
        # nb. we do nothing about OOV items here -- they will be marked by
        # whatever symbols Kaldi knows about, e.g. <unk> in words tier and
        # SPN in phones tier
        tgf = os.path.join(tg_dir, f"{utt}.TextGrid")
        textgrid = TextGrid(tgf)
        word_tier = make_tier("words", utts_word[utt], utt_start, utt_end, '<eps>')
        textgrid.add_tier(word_tier)
        phone_tier = make_tier("phones", utts_phone[utt], utt_start, utt_end, sil_phone)
        textgrid.add_tier(phone_tier)
        tgt.io.write_to_file(textgrid, tgf, format="long")

        # progress bar
        if not (i - 1) % log_interval or i == num_utts:
            log_line_end = '\n' if i == num_utts else '\r'
            n_done = int(i / num_utts * 20)
            print("Creating TextGrids [{}{}] {}/{}".format(
                  n_done * '#', (20 - n_done) * '-', i, num_utts),
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
    parser.add_argument('--workdir', type=str, default='./align',
        help="Working directory for alignment")
    args = parser.parse_args()


    utts_word = load_ctm(args.word_ctm)
    utts_phone = load_ctm(args.phone_ctm)
    utt2dur = load_utt2dur(os.path.join(args.workdir, 'data/train/utt2dur'))

    os.makedirs(args.tg_dir, exist_ok=True)
    write_textgrids(utts_word, utts_phone, utt2dur, args.tg_dir, args.sil)
