#!/usr/bin/env python3

import argparse
import os
import re

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


re_squash_whitespace = re.compile(r'\s+')
#re_split_sentences = re.compile(r'\.(”)? ')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('text', help='Output text directory')
    parser.add_argument('ogg', help='Output Ogg audio directory')
    parser.add_argument('--doc-range', type=int, nargs=2, default=[1, 1216],
        help='Retrieve numbered documents from this range')
    args = parser.parse_args()


    os.makedirs(args.text, exist_ok=True)
    os.makedirs(args.ogg, exist_ok=True)

    first_doc, last_doc = args.doc_range
    #for i in tqdm(range(1, 5), 'Retrieving documents'):
    for i in tqdm(range(first_doc, last_doc + 1), 'Retrieving documents'):
        html_doc = requests.get('https://learngaelic.scot/litir/index.jsp?l={:0>4d}'.format(i))
        soup = BeautifulSoup(html_doc.content, 'html.parser')

        transcript = soup.find(id='gaelictrans')
        transcript_p = transcript.find_all('p')

        with open(os.path.join(args.text, 'litir{:0>4d}.txt'.format(i)), 'w') as outf:
            for p in transcript_p:
                text = p.text.strip()
                #text = re_split_sentences.sub(r'.\1\n', text)
                text = re_squash_whitespace.sub(r' ', text)
                outf.write('{}\n'.format(text))

        audio = soup.find(id='player')
        audio_ogg = audio.find(type='audio/ogg')
        audio_stream = requests.get(audio_ogg['src'], stream=True)
        with open(os.path.join(args.ogg, 'litir{:0>4d}.ogg'.format(i)), 'wb') as outf:
            for chunk in audio_stream.iter_content(chunk_size=1024):
                outf.write(chunk)
