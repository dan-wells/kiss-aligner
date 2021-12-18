#!/usr/bin/env python3

import argparse
import locale
import os
from collections import defaultdict


RESAMPLE_TEMPLATES = {
    'sox': "sox -G {} -c 1 -r {} -e signed-integer -t wav - |",
    'ffmpeg': "ffmpeg -v 24 -i {} -ac 1 -ar {} -acodec pcm_s16le -f wav - |",
    'kaldi': """--sample-frequency={}
--allow-downsample=true
--frame-length=25.0
--frame-shift=10.0
--use-energy=false
""",
}


def audio2utt(audio_path, audio_root, spkr_sep='-', spkr_in_wav=False):
    """Convert audio file path to utterance ID

    Args:
      audio_path: Full path to audio file
      audio_root: Longest common subpath across audio files
      spkr_sep: Character joining speaker ID prefix to utterance ID
      spkr_in_wav: True if speaker ID is already part of audio filename

    Returns:
      utt_id: Utterance ID inferred from audio filename
    """
    utt_id = os.path.relpath(audio_path, audio_root)
    utt_id = os.path.splitext(utt_id)[0]
    if spkr_in_wav:
        # speaker ID is part of wav filename, remove any remaining subdirectory
        utt_id = os.path.basename(utt_id)
    else:
        # subdirectories are per speaker, convert to speaker ID prefix
        utt_id = utt_id.replace(os.path.sep, spkr_sep)
    return utt_id


def process_meta(meta, audio_root, resample=0, resample_method='sox',
                 field_sep=' ', spkr_sep='-', spkr_in_wav=False):
    """Create Kaldi data files from metadata file
    
    Args:
      meta: Path to input metadata file, listing full audio paths and transcripts
      audio_root: Longest common subpath across audio files
      resample: Target sample rate if audio needs converting
      resample_method: Tool to use for resampling audio (sox|ffmpeg|kaldi)
      field_sep: Character separating fields in metadata file
      spkr_sep: Character joining speaker ID prefix to utterance ID
      spkr_in_wav: True if speaker ID is already part of audio filename

    Returns:
      text: Dict mapping utterance IDs to transcripts
      wavscp: Dict mapping utterance IDs to Kaldi extended audio filenames
      utt2spk: Dict mapping utterance IDs to speaker IDs
      spk2utt: Dict mapping speaker IDs to utterance IDs
    """
    text = {}
    wavscp = {}
    utt2spk = {}
    spk2utt = defaultdict(list)
    with open(meta) as inf:
        for line in inf:
            audio_path, *transcript = line.strip().split(field_sep)
            utt_id = audio2utt(audio_path, audio_root, spkr_sep, spkr_in_wav)
            text[utt_id] = ' '.join(transcript)
            speaker = utt_id.split(spkr_sep)[0]
            utt2spk[utt_id] = speaker
            spk2utt[speaker].append(utt_id)
            if not resample or resample_method == 'kaldi':
                wavscp[utt_id] = audio_path
            else:
                wavscp[utt_id] = RESAMPLE_TEMPLATES[resample_method].format(audio_path, resample)
    spk2utt = {spk: ' '.join(utts) for spk, utts in spk2utt.items()}
    return text, wavscp, utt2spk, spk2utt


def write_dict(outdict, outpath):
    """Write dictionary keys and values, sorted consistently with Kaldi

    Args:
      outdict: Dict with data to write
      outpath: Output file path
    """
    # sort as LC_ALL=C for compatibility with Kaldi sorting
    locale.setlocale(locale.LC_ALL, 'C')
    with open(outpath, 'w') as outf:
        for k, v in sorted(outdict.items(), key=lambda x: locale.strxfrm(x[0])):
            outf.write("{} {}\n".format(k, v))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Prepare Kaldi data files from single metadata input",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('meta', type=str,
        help="Path to metadata file listing audio files and transcripts")
    parser.add_argument('audio_root', metavar='audio-root', type=str,
        help="Longest common sub-path for all audio files.")
    parser.add_argument('--workdir', type=str, default='align',
        help="Working directory for alignment, data files will be written "
        "to $workdir/data/train")
    parser.add_argument('--resample', type=int, default=0,
        help="Resample audio to target sampling rate")
    parser.add_argument('--resample-method', type=str,
        choices=['sox', 'ffmpeg', 'kaldi'], default='sox',
        help="Tool to resample audio")
    parser.add_argument('--field-sep', type=str, default=' ',
        help="Character delimiting fields in metadata file (if space, we "
        "only split on the first one)")
    parser.add_argument('--spkr-sep', type=str, default='-',
        help="Character joining speaker ID prefix to utterance ID")
    parser.add_argument('--spkr-in-wav', action='store_true',
        help="If speaker ID is already encoded in wav filename, don't add "
        "any extra prefix")
    args = parser.parse_args()

    datadir = os.path.join(args.workdir, 'data/train')
    os.makedirs(datadir, exist_ok=True)

    text, wavscp, utt2spk, spk2utt = process_meta(
        args.meta, args.audio_root, args.resample, args.resample_method,
        args.field_sep, args.spkr_sep, args.spkr_in_wav)

    write_dict(text, os.path.join(datadir, 'text'))
    write_dict(wavscp, os.path.join(datadir, 'wav.scp'))
    write_dict(utt2spk, os.path.join(datadir, 'utt2spk'))
    write_dict(spk2utt, os.path.join(datadir, 'spk2utt'))

    # write local mfcc.conf for downsampling audio to target rate using Kaldi
    if args.resample and args.resample_method == 'kaldi':
        dataconf = os.path.join(args.workdir, 'conf')
        os.makedirs(dataconf, exist_ok=True)
        with open(os.path.join(dataconf, 'mfcc.conf'), 'w') as mfcc_conf:
            mfcc_conf.write(RESAMPLE_TEMPLATES['kaldi'].format(args.resample))

