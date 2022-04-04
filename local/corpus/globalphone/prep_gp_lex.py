#!/usr/bin/env python3

import argparse

from globalphone import GlobalPhoneLex

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert GlobalPhone pronunciation dictionaries to Kaldi-friendly format')
    parser.add_argument('lex_in', type=str, help='Path to GlobalPhone pronunciation dictionary')
    parser.add_argument('lang', type=str, help='GlobalPhone language code')
    parser.add_argument('lex_out', type=str, help='Path to write output lexicon')
    parser.add_argument('--phone_set', type=str, choices=['gp', 'ipa'], default=None,
        help='Map language-specific phone sets to GlobalPhone or IPA symbols')
    parser.add_argument('--keep-tone', action='store_true', help='Keep tone tags')
    parser.add_argument('--keep-length', action='store_true', help='Keep length tags')
    args = parser.parse_args()

    lex = GlobalPhoneLex(args.lex_in, args.lang, keep_tone=args.keep_tone, keep_length=args.keep_length)
    lex.write_lex(args.lex_out, phone_map=args.phone_set)
