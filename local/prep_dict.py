#!/usr/bin/env python3

import argparse
import os
from collections import defaultdict


def process_lexicon(lexicon, field_sep=' '):
    """Extract word-pronunciation mappings and phone set from lexicon file

    Args:
      lexicon: Input lexicon file mapping words to space-separated phone strings
      field_sep: Character separating words and pronunciations in lexicon

    Returns:
      lex: Dict mapping words to sets of phone strings
      phones: Phone set
    """
    lex = defaultdict(set)  # account for multiple pronunciations
    phones = set()
    with open(lexicon) as inf:
        for line in inf:
            word, pron = line.strip().split(field_sep, maxsplit=1)
            lex[word].update([pron])
            phones.update(pron.split(' '))
    return lex, phones


def write_lexicon(lex, lexdir, oov):
    """Write lexicon file with added OOV entry

    Args:
      lex: Dict mapping words to sets of phone strings
      lexdir: Output directory
      oov: List with token and phone symbol for out-of-vocabulary items
    """
    entry_template = "{} {}\n"
    with open(os.path.join(lexdir, 'lexicon.txt'), 'w') as outf:
        outf.write(entry_template.format(*oov))
        for word, pron_set in sorted(lex.items()):
            for pron in pron_set:
                outf.write(entry_template.format(word, pron))


def write_phones(phones, lexdir):
    """Write phone set listing
    
    Args:
      phone: Phone set
      lexdir: Output directory
    """
    with open(os.path.join(lexdir, 'nonsilence_phones.txt'), 'w') as outf:
        for phone in sorted(phones):
            outf.write("{}\n".format(phone))


def write_sil_phones(oov, lexdir):
    """Write silence phones listing

    Args:
      oov: Phone symbol used for OOV items
      lexdir: Output directory
    """
    with open(os.path.join(lexdir, 'silence_phones.txt'), 'w') as outf:
        for phone in ['SIL', oov]:
            outf.write("{}\n".format(phone))


def write_sil(lexdir):
    """Write optional silence phone listing

    Args:
      lexdir: Output directory
    """
    with open(os.path.join(lexdir, 'optional_silence.txt'), 'w') as outf:
        outf.write("SIL\n")


def write_extraq(lexdir):
    """Touch empty file for extra decision tree questions

    Args:
      lexdir: Output directory
    """
    with open(os.path.join(lexdir, 'extra_questions.txt'), 'w'):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepare Kaldi dictionary files from single lexicon input",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('lex', type=str,
        help="Path to lexicon file listing words and pronunciations")
    parser.add_argument('--workdir', type=str, default='align',
        help="Working directory for alignment, lexicon files will be written "
        "to $workdir/data/local/dict")
    parser.add_argument('--oov', nargs=2, default=['<unk>', 'SPN'],
        help="Symbol to use for out-of-vocabulary items and its pronunciation")
    parser.add_argument('--field-sep', type=str, default=' ',
        help="Character delimiting fields in lexicon file (if space, we "
        "only split on the first one)")
    args = parser.parse_args()

    lexdir = os.path.join(args.workdir, 'data/local/dict')
    os.makedirs(lexdir, exist_ok=True)

    lex, phones = process_lexicon(args.lex, args.field_sep)

    write_lexicon(lex, lexdir, args.oov)
    write_phones(phones, lexdir)
    write_sil_phones(args.oov[1], lexdir)
    write_sil(lexdir)
    write_extraq(lexdir)

