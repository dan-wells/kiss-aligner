#!/usr/bin/env python3

import locale
import os
import sys

if __name__ == '__main__':
    _, textf, dict_dir = sys.argv

    locale.setlocale(locale.LC_ALL, 'C')

    words = set()
    chars = set()

    os.makedirs(dict_dir, exist_ok=True)

    with open(textf, encoding='utf-8') as inf:
        for line in inf:
            utt, *text = line.strip().split()
            words.update(text)
    
    # NB. we modify all these files after generating to account for punctuation,
    # upper- and lowercase characters etc. a bit more deliberately
    with open(os.path.join(dict_dir, 'lexicon.txt'), 'w', encoding='utf-8') as outf:
        for word in sorted(words):
            pron = list(word)
            outf.write('{} {}\n'.format(word, ' '.join(pron)))
            chars.update(pron)
        outf.write('<unk> SPN\n')

    with open(os.path.join(dict_dir, 'nonsilence_phones.txt'), 'w', encoding='utf-8') as outf:
        for char in sorted(chars):
            outf.write('{}\n'.format(char))
    
    with open(os.path.join(dict_dir, 'optional_silence.txt'), 'w', encoding='utf-8') as outf:
        outf.write('SIL\n')
    
    with open(os.path.join(dict_dir, 'silence_phones.txt'), 'w', encoding='utf-8') as outf:
        outf.write('SIL\nSPN\n')
    
    with open(os.path.join(dict_dir, 'extra_questions.txt'), 'a', encoding='utf-8') as outf:
        pass  # touch empty file
