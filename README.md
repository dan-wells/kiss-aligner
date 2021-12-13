# KISS Aligner

Just a simple Kaldi recipe for forced alignment

## Requirements

Bring your own:

- [Kaldi](https://github.com/kaldi-asr/kaldi)
- Audio files with utterance-aligned text transcripts
- Lexicon

## Environment setup

Modify `path.sh` so that `KALDI_ROOT` points to your local Kaldi installation.
Running `path.sh` for the first time will create symbolic links here to the WSJ
`steps` and `utils` directories whose scripts provide the basis for most Kaldi
recipes.

**Note:** You should run the aligner from this directory so that all relative
paths in the standard `egs` scripts resolve correctly. You can specify where to
write output data by passing the `--workdir` argument to `run.sh` (by default it
will create a new directory `align` here to work in).

## Data preparation

To get started, you need to prepare your target dataset according to the
instructions given [here](https://kaldi-asr.org/doc/data_prep.html).
We recommend reading that page for full details of required files!

**TODO:** Automate this process so that you need only provide a simple metadata
file and lexicon in standard formats.

See `local/corpus/vctk_data_prep.sh` and `local/lexicon/cmudict_prep.sh` for
sample scripts building these directories.

### Training data

Below are the files you need to create relating to the audio and text files in
your training corpus. All files should be placed under the `$workdir` you would
like to use for aligning your data. Data fields in all files are space-separated.

- `data/train/text`
    * Lists utterances by ID along with their text transcripts 
    * Normalize text to whatever degree you find agreeable -- it's up to you to
      make it match your lexicon entries, we won't touch it!
    * If you have speaker information, add it as a prefix to utterance IDs
- `data/train/wav.scp`
    * Lists utterances by ID with Kaldi "extended filenames" leading to
      wav-format audio
    * Extended filenames can either be a simple path or a pipe expression
      providing a command which gives wav data on stdout, e.g. using `sox`
- `data/train/utt2spk`
    * Lists utterances by ID with corresponding speaker IDs, one utterance per
      line
    * If you don't have speaker information per utterance, then use utterance ID
      as speaker ID also
- `data/train/spk2utt`
    * Lists all utterances spoken by each speaker ID, one speaker per line
    * Create this like `utils/utt2spk_to_spk2utt.pl data/train/utt2spk >
      data/train/spk2utt`

**Note:** All files under `data/train` need to be sorted in a consistent manner,
otherwise Kaldi will fail to process them properly. For example, you could
`export LC_ALL=C` in your shell and run each through `sort` to make sure this is
the case.

The above assumes you already have audio data split one file per utterance. If
instead you have long recordings but know already where each utterance starts
and ends, then you should also create a `data/train/segments` file with that
information. The alignment recipe provided should handle this alternative but
also standard approach just fine without any modification.

### Lexicon

Below are the files you need to create relating to the lexicon providing
pronunciations for all words in your training corpus. Again, all files should be
placed under your output `$workdir`.

- `data/local/dict/lexicon.txt`
    * Pronunciation dictionary mapping words to phone strings
    * Should include an entry for a special out-of-vocabulary (OOV) symbol in
      case there are words in your corpus not covered by the lexicon, e.g.
      `<unk> SPN`.
    * If you don't want to find OOV symbols in the final alignments, then
      make sure your lexicon contains some pronunciation for every word in
      your corpus! We don't (yet) try and train any g2p to fill in the gaps. 
- `data/local/dict/nonsilence_phones.txt`
    * Lists all phones found in the lexicon
- `data/local/dict/optional_silence.txt`
    * Specifies symbol to use for optional silences inserted between words
- `data/local/dict/silence_phones.txt`
    * Lists silence symbols, including optional silence and the symbol you
      chose to represent the pronunciation of OOV words (`SPN` in our example
      above)
- `data/local/dict/extra_questions.txt`
    * This can be an empty file, but would be the place to note phone variants
      due to stress, tone etc.

These files will be used to prepare the `data/lang` directory in the first stage
of `run.sh`, using `utils/prepare_lang.sh`.

**Note:** By default we set the OOV symbol to be `<unk>`. If you choose a
different symbol for your lexicon, then make sure to specify the `--oov` option
when you run the main alignment script.

## Usage

Once the directories under `$workdir/data/train` and `$workdir/data/local/dict`
have been set up, call the main run script like so:

```sh
run.sh --workdir $workdir
```

This should do all the necessary checking of the data files you have provided
and continue to run the full alignment process! The final outputs will be
per-utterance CTM files at both word- and phone-level alignments, placed under
`$workdir/{word,phone}`.

If something goes wrong and you need to restart the script but don't want to
redo previous work, then pass the `--stage` argument to `run.sh` specifying
where you want to pick up from.

Check `run.sh --help` to see all available options.

**Note:** Not all utterances may be successfully aligned! In that case, there
will simply be missing CTM files in the final output. You can find warnings
about any failed alignments in the logs:

```sh
grep "Did not successfully decode file" \
  $workdir/exp/tri4b_ali_train/log/align_pass2.*.log
```

## Acknowledgments

- Sample Kaldi recipes in `egs/{librispeech,wsj}` which provided the basic
  skeleton for this script and several interesting ideas for further development
- Thorough [Kaldi documentation](https://kaldi-asr.org/doc/index.html), especially on data preparation
- [Eleanor Chodroff's Kaldi tutorial](https://eleanorchodroff.com/tutorial/kaldi/index.html)
  for explicitly laying out all the individual steps in the process, and
  specifically for the instructions to
  [extract phone-level CTM files from alignments](https://www.eleanorchodroff.com/tutorial/kaldi/forced-alignment.html#extract-alignment).
