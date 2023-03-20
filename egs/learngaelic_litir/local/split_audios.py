#!/usr/bin/env python

import argparse
import os
from glob import glob

from pydub import AudioSegment
from pydub.silence import split_on_silence
from tqdm import tqdm


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('audio_in', help='Directory containing long input audio files')
    parser.add_argument('audio_out', help='Directory to write output segmented audio')
    args = parser.parse_args()

    audio_files = sorted(glob(os.path.join(args.audio_in, '*.wav')))
    for audio_file in tqdm(audio_files, 'Splitting audio'):
        audio = AudioSegment.from_wav(audio_file)

        audio_basename, _ = os.path.splitext(os.path.basename(audio_file))
        chunk_dir = os.path.join(args.audio_out, audio_basename)
        os.makedirs(chunk_dir, exist_ok=True)

        #print('Finding silences...')
        chunks = split_on_silence(audio, min_silence_len=1500, keep_silence=500,
                                  silence_thresh=audio.dBFS - 16)
        #for i, chunk in tqdm(enumerate(chunks, 1), 'Writing chunks', len(chunks)):
        for i, chunk in enumerate(chunks, 1):
            chunk_file = '{}_{:0>4d}.wav'.format(audio_basename, i)
            chunk.export(os.path.join(chunk_dir, chunk_file), format='wav',
                         parameters=['-ar', '16000', '-sample_fmt', 's16'])
