#!/usr/bin/env python3

import argparse
import glob
import os
import wave
from itertools import groupby

import dtw


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('audio_in', help='Directory containing segmented audio files')
    parser.add_argument('text_in', help='Directory containing segmented text transcripts')
    parser.add_argument('data_out', help='Output Kaldi data directory')
    args = parser.parse_args()

    os.makedirs(args.data_out, exist_ok=True)
    out_textf = os.path.join(args.data_out, 'text_raw')
    out_wavf = os.path.join(args.data_out, 'wav.scp')

    with open(out_textf, 'w') as out_text, open(out_wavf, 'w') as out_wav:
        chunked_litirs = glob.glob(os.path.join(args.audio_in, '*'))
        for audio_dir in sorted(chunked_litirs):
            litir = os.path.basename(audio_dir)
            litir_id = int(litir.lstrip('litir'))
            textf = os.path.join(args.text_in, '{}.txt'.format(litir))

            audios = sorted(glob.glob(os.path.join(audio_dir, '*.wav')))
            audio_lens = []
            total_audio_len = 0
            for i, audio in enumerate(audios):
                if i == 0 and litir_id >= 307:
                    continue  # try and skip preambles
                with wave.open(audio) as inf:
                    dur = inf.getnframes() / inf.getframerate()
                    total_audio_len += dur
                    audio_lens.append(total_audio_len)
            audio_lens = [i / total_audio_len for i in audio_lens]

            texts = []
            text_lens = []
            total_text_len = 0
            with open(textf) as inf:
                for line in inf:
                    if line.startswith(litir):
                        text = line.strip().split(maxsplit=1)
                        texts.append(text)
                        total_text_len += len(text[1])
                        text_lens.append(total_text_len)
                    else:
                        break
            text_lens = [i / total_text_len for i in text_lens]

            alignment = dtw.dtw(audio_lens, text_lens)

            prev_audio = ''
            prev_text = []
            for i, j in zip(alignment.index1, alignment.index2):
                if litir_id >= 307:
                    i += 1  # skip preamble
                if prev_audio != audios[i] and prev_text:
                    #print(prev_audio, '|'.join(prev_text))
                    utt_id = os.path.splitext(os.path.basename(prev_audio))[0]
                    out_text.write('{} {}\n'.format(utt_id , ' '.join(prev_text)))
                    out_wav.write('{} {}\n'.format(utt_id, prev_audio))
                    prev_text = []
                prev_text.append(texts[j][1])
                prev_audio = audios[i]
            #print(prev_audio, '|'.join(prev_text))
            utt_id = os.path.splitext(os.path.basename(prev_audio))[0]
            out_text.write('{} {}\n'.format(utt_id, ' '.join(prev_text)))
            out_wav.write('{} {}\n'.format(utt_id, prev_audio))
