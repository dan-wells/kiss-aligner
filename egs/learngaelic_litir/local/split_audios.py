#!/usr/bin/env python3

import argparse
import os
from glob import glob
from itertools import repeat
from multiprocessing import Pool

from pydub import AudioSegment
from pydub.silence import split_on_silence
from tqdm import tqdm


def split_audio(args):
    audio_file, audio_out_dir = args
    audio = AudioSegment.from_wav(audio_file)

    audio_basename, _ = os.path.splitext(os.path.basename(audio_file))
    chunk_dir = os.path.join(audio_out_dir, audio_basename)
    os.makedirs(chunk_dir, exist_ok=True)

    #print('Finding silences...')
    chunks = split_on_silence(audio, min_silence_len=1500, keep_silence=500,
                              silence_thresh=audio.dBFS - 16)
    #for i, chunk in tqdm(enumerate(chunks, 1), 'Writing chunks', len(chunks)):
    for i, chunk in enumerate(chunks, 1):
        chunk_file = '{}_{:0>4d}.wav'.format(audio_basename, i)
        chunk.export(os.path.join(chunk_dir, chunk_file), format='wav',
                     parameters=['-ar', '16000', '-sample_fmt', 's16'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('audio_in', help='Directory containing long input audio files')
    parser.add_argument('audio_out', help='Directory to write output segmented audio')
    parser.add_argument('--nj', default=8, help='Number of parallel processes to run')
    args = parser.parse_args()

    audio_files = sorted(glob(os.path.join(args.audio_in, '*.wav')))
    with Pool(args.nj) as pool:
        with tqdm(desc='Splitting audio', total=len(audio_files)) as pbar:
            split_audio_args = zip(audio_files, repeat(args.audio_out))
            for _ in pool.imap(split_audio, split_audio_args):
                pbar.update()
