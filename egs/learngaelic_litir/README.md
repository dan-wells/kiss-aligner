# Building a Scottish Gaelic speech corpus for TTS

This recipe accompanies our paper _A Low-Resource Pipeline for Text-to-Speech
from Found Data with Application to Scottish Gaelic_ (accepted to Interspeech
2023).

The steps are as follows:

- Scrape and download ~100 hours of 5-minute recordings from LearnGaelic's
  [_Litir do Luchd-ionnsachaidh_](https://learngaelic.scot/litir) 'Letter to
  Learners' series, along with text transcripts
- Split recordings on silences longer than 1.5 s, transcripts on punctuation,
  and roughly align
- Train an initial character-based acoustic model on these approximate
  text-audio pairs
- Decode larger audio chunks using initial acoustic model and align hypotheses
  against reference transcripts
- Split recordings and text according to discovered segments

Assuming you've set everything up for the main KISS recipe and installed all
Python requirements, you should be able to replicate this process by calling
`./run.sh` from this directory.

**Note:** The recipe is currently written to run end-to-end, not in individual
stages, so you may want to run each step from `run.sh` manually instead.

## Pre-prepared files

Pre-prepared Kaldi `segments` and `text` files for the corpus used in our paper
are available for download [here](https://wellsd.net/gaelic-tts/learngaelic_litir.tar.gz).

With these, you can recreate the corpus just by downloading the original
unsegmented recordings, converting to WAV format and splitting them according
to the `segments` file, so skipping the intermediate alignment steps.

The following snippet should leave you with `text` and `segments` files in the
current directory, a new directory `wavs/` containing segmented audio files,
and temporary files representing the unsegmented recordings under
`data/{text_long/,ogg_long/,wav_long/,wav_long.scp}`.

```sh
local/scrape_transcripts_and_audios.py \
  --doc-range 1 1216 data/text_long data/ogg_long

mkdir -p data/wav_long
for ogg in data/ogg_long/*.ogg; do
  wav=${ogg##*/}
  wav=${wav/.ogg/.wav}
  sox -G $ogg -b 16 -c 1 -r 16k data/wav_long/$wav
  echo "${wav%.wav} data/wav_long/$wav" >> data/wav_long.scp
done

wget "https://wellsd.net/gaelic-tts/learngaelic_litir.tar.gz"
tar -xzf learngaelic_litir.tar.gz

local/segments_to_wavs.py segments data/wav_long.scp wav
```
