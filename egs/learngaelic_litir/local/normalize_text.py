#!/usr/bin/env python3

import argparse
import re
import string
from unicodedata import normalize

#from unidecode import unidecode


target_punc = ''.join(i for i in string.punctuation if i not in "'-:") + '°'
strip_punc_table = str.maketrans('', '', target_punc)

# note: this excludes smart quotes, en- and em-dashes
re_ascii_check = re.compile(r'^[\w\s!"#$%&\\\'\(\)\*\+,\-\./:;<=>\?@\[\]\^_`\{|\}~]+$', flags=re.A)
re_digit_check = re.compile(r'\d')
re_squash_apostrophe = re.compile(r"'+")
re_punc_to_space = re.compile(r'[-:]')
re_strip_apostrophe = re.compile(r"(^'|'$|'\s+'|'\W|\W')")
re_pad_punc = re.compile(r"([^\w\d'-])")
re_squash_spaces = re.compile(r'\s+')

sub_single_quotes = re.compile(r'[ʼ‘’̓̕\u0313\u0315]')  # some awkward combining marks
sub_double_quotes = re.compile(r'[“”]')
sub_dashes = re.compile(r'[–—]')
sub_ellipses = re.compile(r'…')
sub_digits = re.compile(r'\d+')


def load_text(text_file, sep=' '):
    utt_text = {}
    with open(text_file) as inf:
        for line in inf:
            utt, text = line.strip().split(sep, maxsplit=1)
            utt_text[utt] = text
    return utt_text


def write_text(utt_text, text_file):
    with open(text_file, 'w', encoding='utf8') as outf:
        for utt, text in utt_text.items():
            outf.write('{} {}\n'.format(utt, text))


def normalize_text(text, lowercase=False, strip_punc=False, strip_apos=False,
                   mark_space=False, skip_non_ascii=False, replace_digits=False):
    #if skip_non_ascii:
    #    all_ascii = re_ascii_check.match(text)
    #    if all_ascii is None:
    #        return ''

    #if skip_digits:
    #    digit_check = re_digit_check.search(text)
    #    if digit_check is not None:
    #        return ''

    # accents mark length(/quality) in Gaelic, so don't convert to ascii
    #text = unidecode(text)
    text = normalize('NFC', text)  # combine diacritics

    text = sub_single_quotes.sub("'", text)
    text = sub_double_quotes.sub('"', text)
    text = sub_dashes.sub('-', text)
    text = sub_ellipses.sub('...', text)

    if strip_punc:
        text = text.translate(strip_punc_table)
        text = re_punc_to_space.sub(' ', text)
        text = re_squash_apostrophe.sub("'", text)
    #if strip_apos:
    #    text = re_strip_apostrophe.sub(' ', text)

    # add spaces around punctuation
    text = re_pad_punc.sub(r" \1 ", text)

    if mark_space:
        space_char = '_'
    else:
        space_char = ' '
    text = re_squash_spaces.sub(space_char, text)

    if lowercase:
        text = text.lower()

    if replace_digits:
        text = sub_digits.sub('NUMBER', text)  # would like still to try and align these docs

    return text


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_text', type=str, help='Input text file')
    parser.add_argument('text', type=str, help='Output text file')
    parser.add_argument('--field_sep', type=str, default=' ', help='Input field separator')
    parser.add_argument('-v', '--verbose', action='store_true', help='Advise of skipped utterances')
    args = parser.parse_args()

    utt_text = load_text(args.raw_text, args.field_sep)
    print('Loaded {} utterances'.format(len(utt_text)))

    print('Normalizing utterances...')
    utt_text_clean = {}
    for utt, text in utt_text.items():
        clean_text = normalize_text(text).strip()
        if clean_text:
            utt_text_clean[utt] = clean_text
        elif args.verbose:
            print('  Skipped {}: {}'.format(utt, text))

    print('Kept {} utterances'.format(len(utt_text_clean)))
    write_text(utt_text_clean, args.text)
