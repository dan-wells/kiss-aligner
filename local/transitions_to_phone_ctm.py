#!/usr/bin/env python3

import argparse
import gzip
import os
import re


re_state = re.compile(r'Transition-state (\d+): phone = (.+) hmm-state = (\d+) pdf = (\d+)')
re_trans = re.compile(r' Transition-id = (\d+) .* \[(.+)\]')
re_wb = re.compile(r'_[BIES]$')


def load_ali_gz(ali):
    """Load gzipped state transition sequences for multiple utterances

    Args:
      ali: Path to gzipped output from convert-ali

    Returns:
      utt_ali: Dict mapping utterance IDs to state transition sequences
    """
    utt_ali = {}
    with gzip.open(ali, 'rt') as f:
        lines = f.read().split('\n')
        for line in lines:
            utt, *trans = line.strip().split(' ')
            if utt:
                utt_ali[utt] = [int(i) for i in trans]
    return utt_ali


def parse_transitions(trans, strip_wb=True):
    """Generate map from integer state transition IDs to phone labels
    
    Args:
      trans: Path to file listing state transition information, generated
        by show-transitions
      strip_wb: If True, strip word position tags from phone labels

    Returns:
      trans_phone: Dict mapping integer state transition IDs to tuples
        like (phone, state), where state is the one we have just transitioned
        into, and is one of the emitting states of the given phone HMM
    """
    trans_phone = {}
    with open(trans) as inf:
        for line in inf:
            match_state = re_state.match(line)
            if match_state is not None:
                state_id, phone, hmm_state, pdf = match_state.groups()
                if strip_wb:
                    # strip word position tag from phone labels
                    phone = re_wb.sub('', phone)
                continue
            match_trans = re_trans.match(line)
            if match_trans is not None:
                trans_id, end_state = match_trans.groups()
                if end_state == 'self-loop':
                    end_state = hmm_state
                else:
                    end_state = end_state.split()[-1]
                trans_phone[int(trans_id)] = (phone, end_state)
    return trans_phone


def trans_id_to_phone(ali, trans_phone):
    """Convert state transition sequence to phone states for one utterance

    Args:
      ali: Sequence of integer state transition IDs
      trans_phone: Dict mapping integer state transition IDs to phone labels

    Returns:
      phone_states: List of strings representing the phone state alignment
        for a given utterance. Elements like 'k_0' for the first emitting
        state of a phone labelled /k/.
    """
    phone_states = []
    for prev_trans, curr_trans in zip(ali, ali[1:]):
        prev_phone, prev_state = trans_phone[prev_trans]
        curr_phone, curr_state = trans_phone[curr_trans]
        if curr_phone != prev_phone:
            # transition from final non-emitting state of prev_phone to
            # first emitting state of curr_phone => label with curr_phone
            phone_states.append("{}_0".format(curr_phone))
        else:
            phone_states.append("{}_{}".format(prev_phone, prev_state))
    # final state is non-emitting => don't need it, no frame
    #phone_states.append("{}_{}".format(curr_phone, curr_state))
    return phone_states


def phone_to_ctm(ali, frame_shift, out_dir, utt):
    """Write phone state sequences to CTM file
    
    Args:
      ali: Sequence of phone states for one utterance
      frame_shift: Frame shift in milliseconds, to calculate durations
      out_dir: Output directory to write CTM file
      utt: Utterance ID, also used for CTM file name
    """
    ctm_line = "{} 1 {:.3f} {:.3f} {}\n"
    frame_shift = frame_shift / 1000
    start = 0
    dur = frame_shift
    with open(os.path.join(out_dir, utt), 'w') as outf:
        for prev_phone, curr_phone in zip(ali, ali[1:]):
            dur += frame_shift
            if curr_phone != prev_phone:
                outf.write(ctm_line.format(utt, start, dur, prev_phone))
                start += dur
                dur = 0
        dur += frame_shift
        outf.write(ctm_line.format(utt, start, dur, curr_phone))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Convert state transition alignment files to phone-state CTM",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('transitions', type=str,
        help='File listing state transition information for the alignment model, '
        'as generated by show-transitions')
    parser.add_argument('ali_dir', type=str,
        help='Directory containing alignment files')
    parser.add_argument('out_dir', type=str,
        help='Output directory to write per-utterance CTM files')
    parser.add_argument('--frame-shift', type=float, default=10.0,
        help='Frame shift used during alignment feature extraction, in milliseconds')
    parser.add_argument('--nj', type=int, default=4,
        help='Number of parallel jobs run during alignment, i.e. how many split ali '
        'files to process')
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    trans_phone = parse_transitions(args.transitions)
    for i in range(1, args.nj + 1):
        utt_ali = load_ali_gz(os.path.join(args.ali_dir, 'ali.trans.{}.gz'.format(i)))
        for utt, ali in utt_ali.items():
            phone_states = trans_id_to_phone(ali, trans_phone)
            phone_to_ctm(phone_states, args.frame_shift, args.out_dir, utt)

