#!/usr/bin/env python

import argparse
import os
import shutil
import wave
from collections import defaultdict

from tqdm import tqdm


def read_segments(segments_file):
    segments = defaultdict(list)
    with open(segments_file) as inf:
        for line in inf:
            seg, src_audio, start, end = line.strip().split()
            segments[src_audio].append((seg, float(start), float(end)))
    return dict(segments)


def read_scp(scp_file):
    utt_wavs = {}
    with open(scp_file) as inf:
        for line in inf:
            utt, wav = line.strip().split()
            utt_wavs[utt] = wav
    return utt_wavs


def get_audio_params(wavf):
    nchannels = wavf.getnchannels()
    sampwidth = wavf.getsampwidth()
    framerate = wavf.getframerate()
    return nchannels, sampwidth, framerate


def set_audio_params(wavf, nchannels, sampwidth, framerate):
    wavf.setnchannels(nchannels)
    wavf.setsampwidth(sampwidth)
    wavf.setframerate(framerate)


def split_audios(segments, wav_scp, wav_out):
    pbar = tqdm(desc='Extracting audio segments', total=sum(len(i) for i in segments.values()))
    utt_wavs = read_scp(wav_scp)
    for src_audio, wav_path in utt_wavs.items():
        if src_audio not in segments:
            continue  # no discovered segments
        with wave.open(wav_path) as wavf:
            c, b, r = get_audio_params(wavf)
            for segment, start, end in segments[src_audio]:
                # seek source audio
                wavf.setpos(int(start * r))
                wavf_seg = wavf.readframes(int((end - start) * r))
                audio_seg = os.path.join(wav_out, segment + '.wav')
                with wave.open(audio_seg, 'wb') as segf:
                    set_audio_params(segf, c, b, r)
                    segf.writeframes(wavf_seg)
                pbar.update(1)
    pbar.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('segments', type=str,
        help='Kaldi segments file')
    parser.add_argument('wav_scp', type=str,
        help='Kaldi wav.scp pointing to unsegmented WAV files')
    parser.add_argument('wav_out', type=str,
        help='Directory to write segmented WAV files')
    parser.add_argument('--rm', action='store_true',
        help='Delete existing wav_out directory (speeds up writing pre-existing files)')
    args = parser.parse_args()

    segments = read_segments(args.segments)

    if args.rm:
        print("Deleting existing output directory...")
        shutil.rmtree(args.wav_out)
    os.makedirs(args.wav_out, exist_ok=True)

    split_audios(segments, args.wav_scp, args.wav_out)
