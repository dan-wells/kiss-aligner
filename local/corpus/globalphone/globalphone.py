#!/usr/bin/env python3

"""
Utilities for working with GlobalPhone pronunciation dictionaries.
"""

import re
from collections import defaultdict, OrderedDict


# NB. These encodings are correct for the versions of GlobalPhone dictionaries
# stored in University of Edinburgh School of Informatics group corpora space
_ENCODINGS = {
    'AR': 'ascii',      # Arabic
    'BG': 'utf-8',      # Bulgarian
    'CR': 'ascii',      # Croatian
    'CZ': 'iso-8859-1', # Czech
    'FR': 'iso-8859-1', # French
    'GE': 'iso-8859-1', # German
    'HA': 'ascii',      # Hausa
    'JA': 'ascii',      # Japanese
    'KO': 'ascii',      # Korean
    'MA': 'ascii',      # Mandarin
    'PL': 'utf-8',      # Polish
    'PO': 'ascii',      # Portuguese
    'RU': 'ascii',      # Russian
    'SA': 'ascii',      # Swahili
    'SP': 'ascii',      # Spanish
    'SW': 'ascii',      # Swedish
    'TH': 'utf-8',      # Thai
    'TU': 'ascii',      # Turkish
    'UK': 'utf-8',      # Ukrainian
    'VI': 'utf-8',      # Vietnamese
}

# Extract individual phones (possibly wrapped in {} with tags) from full
# pronunciation entry. Character ~ used in old French dictionary for nasal
# vowels, + in some annotations for non-speech sounds, : for syllable
# boundaries in Thai, / in some markup for many Korean pronunciations
_re_extract_phones = re.compile(r'{[\w~+:/ ]+}|[\w~+:/]+')

# Remove phone set label (e.g. M_ for language-independent phones, SWA_ for
# Swahili phones) from individual phone string
_re_strip_phone_set = re.compile(r'\w+?_([\w~+]+)')

# Remove unknown /1 annotation from initial phones of many Korean entries
_re_strip_ko_1 = re.compile(r'/1$')

# Remove syllable boundary markers from Thai entries
# TODO: Handle these as tags?
_re_strip_th_sb = re.compile(r':sb')

# Tags for word and syllable boundaries, length markers and tone variants
_re_wb = re.compile(r'WB')
_re_length = re.compile(r'(L|S)')
_re_tone = re.compile(r'(T\d)')

# Tags for variant pronunciations
_re_pronvar = re.compile(r'\(\d\)$')


class GlobalPhoneLex():
    def __init__(self, lex_file, lang_code, keep_wb=False, keep_tone=False,
                 keep_length=False, map_ipa=True):
        self.lex_file = lex_file
        self.lang_code = lang_code
        self.encoding = _ENCODINGS[lang_code]

        self.keep_wb = keep_wb
        self.keep_tone = keep_tone
        self.keep_length = keep_length
        self.tag_order = ['WB', 'T', 'L']

        self.lex, self.phone_set = self.load_lex()
        if map_ipa:
            self.ipa_phone_map = self.get_ipa_phone_map()
            self.ipa_phone_set = self.get_ipa_phone_set()

    # TODO: inherit from collections.UserDict or
    #       collections.abc.[Mutable]Mapping instead?
    def __getitem__(self, key):
        return self.lex[key]

    def load_lex(self):
        # just in case there are duplicate alternate prons: preserve order
        # (e.g. might be based on frequency), but remove duplicates
        lex = defaultdict(OrderedDict)
        phone_set = set()
        non_phones = {'SIL', 'WB', '+QK', '+hGH'}
        with open(self.lex_file, encoding=self.encoding) as inf:
            for entry in inf:
                # TODO: check if there are ever spaces in dictionary keys
                entry = entry.split()
                key, pronstr = entry[0].strip('{}'), ' '.join(entry[1:])
                key = re.sub(_re_pronvar, '', key)
                pronstr = self.clean_pronstr(pronstr)
                lex[key][pronstr] = None
                phone_set.update(pronstr.split())
        phone_set = phone_set.difference(non_phones)
        # list of deduplicated prons per word, with original order intact
        lex = {i: list(j.keys()) for i, j in lex.items()}
        return lex, phone_set

    def write_lex(self, path, phone_map=False):
        with open(path, 'w', encoding='utf-8') as outf:
            for word in self.lex:
                if phone_map:
                    prons = self.map_prons(word, phone_map)
                else:
                    prons = self.lex[word]
                for pron in prons:
                    outf.write('{} {}\n'.format(word, pron))

    def clean_pronstr(self, pronstr):
        phones = []
        for phone in re.findall(_re_extract_phones, pronstr):
            # phones with word boundary, length or tone tags
            if phone.startswith('{'):
                phone = phone.strip('{}')
                phone_tags = phone.split()
                phone, tags = phone_tags[0], phone_tags[1:]
                if self.keep_wb or self.keep_length or self.keep_tone:
                    tag_str = self.filter_tags(tags)
                    phone = phone + tag_str
            stripped_phone = re.match(_re_strip_phone_set, phone)
            if stripped_phone is not None:
                phone = stripped_phone.group(1)
            phones.append(phone)
        if self.lang_code == 'KO':
            phones[0] = re.sub(_re_strip_ko_1, '', phones[0])
        phone_str = ' '.join(phones)
        if self.lang_code == 'TH':
            phone_str = re.sub(_re_strip_th_sb, '', phone_str)
        return phone_str

    def filter_tags(self, tags):
        keep_tags = {}
        for tag in tags:
            # TODO: this is somehow broken for Thai
            if self.keep_wb:
                match_wb = re.match(_re_wb, tag)
                if match_wb is not None:
                    keep_tags['WB'] = 'WB'
                    continue # any tag can only match a single pattern
            # TODO: handle Mandarin/Thai tone markup
            if self.keep_tone:
                match_tone = re.match(_re_tone, tag)
                if match_tone is not None:
                    keep_tags['T'] = match_tone.group(1)
                    continue
            if self.keep_length:
                match_length = re.match(_re_length, tag)
                if match_length is not None:
                    keep_tags['L'] = match_length.group(1)
                    continue
        # don't know if GlobalPhone languages use consistent
        # tag ordering, so just in case we enforce it here
        tag_str = ''
        for tag in self.tag_order:
            try:
                tag_str += f'_{keep_tags[tag]}'
            except KeyError:
                continue
        return tag_str

    def get_ipa_phone_map(self):
        gp_phone_map = lang2gp[self.lang_code]
        ipa_phone_map = {}
        for phone in self.phone_set:
            if phone in gp_phone_map:
                # some non-standard phones might expand to a sequence
                gp_phones = gp_phone_map[phone].split()
                ipa_phone_map[phone] = ' '.join(gp2ipa[i] for i in gp_phones)
            else:
                # no need to map any phones which already match GP conventions
                ipa_phone_map[phone] = gp2ipa[phone]
        return ipa_phone_map

    def get_ipa_phone_set(self):
        ipa_phone_set = set()
        for phone_seq in self.ipa_phone_map.values():
            ipa_phone_set.update(phone_seq.split())
        return ipa_phone_set

    def pron_ipa(self, word):
        prons = self[word]
        ipa_prons = []
        for pron in prons:
            ipa_pron = ' '.join(self.ipa_phone_map[p] for p in pron.split())
            # clean up any extra spaces, e.g. from suppressed phones
            ipa_pron = re.sub(r'\s+', ' ', ipa_pron.strip())
            ipa_prons.append(ipa_pron)
        return ipa_prons

    def map_prons(self, word, phone_map='ipa'):
        if phone_map == 'ipa':
            phone_map = self.ipa_phone_map
        elif phone_map == 'gp':
            phone_map = lang2gp[self.lang_code]
        else:
            phone_map = {}
        prons = self[word]
        mapped_prons = []
        for pron in prons:
            mapped_pron = []
            for phone in pron.split():
                try:
                    mapped_pron.append(phone_map[phone])
                except KeyError:
                    mapped_pron.append(phone)
            mapped_pron = ' '.join(mapped_pron)
            mapped_pron = re.sub(r'\s+', ' ', mapped_pron.strip())
            mapped_prons.append(mapped_pron)
        return mapped_prons


# Phone set mappings

# IPA compatible with panphon
gp2ipa = {
    'p': 'p', 'b': 'b', 't': 't', 'd': 'd', 'k': 'k', 'g': 'ɡ', 'Q': 'ʔ',
    'ph': 'pʰ', 'th': 'tʰ', 'kh': 'kʰ', 'pj': 'pʲ', 'tj': 'tʲ', 'kj': 'kʲ',
    'pes': 'pʼ', 'tes': 'tʼ', 'kes': 'kʼ',
    'm': 'm', 'n': 'n', 'nj': 'ɲ', 'ng': 'ŋ', 'nq': 'ɴ',
    'r': 'r', 'rf': 'ɾ', 'l': 'l', 'L': 'ʎ', 'j': 'j', 'w': 'w', '9r': 'ɻ', 'j4': 'ɰ',
    'F': 'ɸ', 'V': 'β', 'f': 'f', 'v': 'v', 'T': 'θ', 'D': 'ð', 's': 's', 'z': 'z',
    'S': 'ʃ', 'Z': 'ʒ', 'sr': 'ʂ', 'C': 'ç', 'x': 'x', 'G': 'ɣ', 'rk': 'ʁ', 'h': 'h',
    'ts': 't͡s', 'tS': 't͡ʃ', 'dz': 'd͡z', 'dZ': 'd͡ʒ',
    'cp': 'ɕ', 'zp': 'ʑ', 'tcp': 't͡ɕ', 'dzp': 'd͡ʑ',
    # additional language-specific consonants
    'Hq': 'ʕ', 'H': 'ħ', 'sq': 'sˤ', 'Dq': 'ðˤ', 'dq': 'dˤ', 'tq': 'tˤ',
    'bj': 'bʲ', 'dj': 'dʲ', 'fj': 'fʲ', 'gj': 'gʲ', 'lj': 'lʲ', 'mj': 'mʲ',
    'nJ': 'nʲ', 'rj': 'rʲ', 'sj': 'sʲ', 'vj': 'vʲ', 'zj': 'zʲ',
    'vp': 'ʋ', 'mp': 'ɱ', 'jp': 'ɥ', 'J': 'ɟ', 'c': 'c', 'q': 'q',
    'rzh': 'r̻', 'hv': 'ɦ', 'B': 'ɓ', 'Dv': 'ɗ', 'ces': 'cʼ', 'rrf': 'ɽ',
    'tcph': 't͡ɕʰ', 'trsr': 'ʈ͡ʂ', 'trsrh': 'ʈ͡ʂʰ', 'tsh': 't͡sʰ',
    'zr': 'ʐ', 'drzr': 'ɖ͡ʐ', 'gv': 'ɠ', 'Jv': 'ʄ', 'sx': 'ɧ', 'lr': 'ɭ',
    'nr': 'ɳ', 'rtu': 'ɹ', 'dr': 'ɖ͡', 'tr': 'ʈ͡', 'tsj': 't͡sʲ', 'dzj': 'd͡zʲ',
    'hvj': 'ɦʲ', 'Sj': 'ʃʲ', 'tSj': 't͡ʃʲ', 'vpj': 'ʋʲ', 'xj': 'xʲ', 'Zj': 'ʒʲ',

    'i': 'i', 'ue': 'y', 'i2': 'ɨ', 'W': 'ɯ', 'u': 'u', 'ip': 'ɪ', 'vst': 'ʊ',
    'e': 'e', 'oe': 'ø', 'etu': 'ɘ', 'o': 'o',
    'ae': 'ɛ', 'ole': 'œ', 'ov': 'ʌ', 'oc': 'ɔ',
    'ale': 'æ', 'atu': 'ɐ', 'a': 'a', 'ab': 'ɑ',
    'aI': 'a i', 'aU': 'a u', 'eI': 'e i', 'eU': 'e u', 'oI': 'o i',
    # additional language-specific vowels
    'ii': 'iː', 'aa': 'aː', 'ee': 'eː', 'oo': 'oː', 'uu': 'uː', 'WW': 'ɯː',
    'aeae': 'ɛː', 'oeoe': 'øː', 'ueue': 'yː', 'abab': 'ɑː', 'aleale': 'æː',
    'oleole': 'œː', 'uxux': 'ʉː', 'YY': 'ɤː', 'ococ': 'ɔː', 'axax': 'əː',
    'abn': 'ɑ̃', 'aen': 'ɛ̃', 'olen': 'œ̃', 'ocn': 'ɔ̃', 'atun': 'ɐ̃', 'en': 'ẽ',
    'ipn': 'ɪ̃', 'on': 'õ', 'un': 'ũ', 'vstn': 'ʊ̃',
    'Y': 'ɤ', 'ax': 'ə', 'uep': 'ʏ', 'ox': 'ɵ',
}

lang2gp = {
    'AR': {
        'C': 'S', 'Cl': 'S S', 'rr': 'G', 'G': 'dZ',
        'S': 'sq', 'Sl': 'sq sq', 'Z': 'Dq', 'dl': 'dq', 'tl': 'tq',
        'il': 'ii', 'al': 'aa', 'alal': 'aa', 'ul': 'uu',
        'll': 'l l', 'ml': 'm m', 'nl': 'n n', 'rl': 'r r', 'sl': 's s',
    },
    'BG': {
        'ja': 'j a', 'ju': 'j u', 'nj': 'nJ',
    },
    'CR': {
        'cp': 'tcp', 'dp': 'dzp', 'sj': 'S', 'zj': 'Z', 'v': 'vp',
    },
    'CZ': {
        'i': 'ip', 'e': 'ae', 'ee': 'aeae', 'aw': 'a u', 'ew': 'ae u', 'ow': 'o u',
        'c': 'ts', 'ch': 'tS', 'dj': 'J', 'h': 'hv', 'mg': 'mp', 'tj': 'c',
        'sh': 'S', 'zh': 'Z', 'rzh': 'rzh', 'rsh': 'rzh',
    },
    'FR': {
        'AE': 'ax', 'AX': 'ax', 'EU': 'oe', 'OE': 'ole', 'E': 'ae', 'O': 'oc',
        'y': 'ue', 'A~': 'abn', 'E~': 'aen', 'OE~': 'olen', 'o~': 'ocn',
        'B': 'b', 'D': 'd', 'F': 'f', 'G': 'g', 'J': 'j', 'K': 'k', 'L': 'l',
        'M': 'm', 'N': 'n', 'NG': 'ng', 'NJ': 'nj', 'P': 'p', 'R': 'rk',
        'S': 's', 'SH': 'S', 'T': 't', 'V': 'v', 'W': 'w', 'Z': 'z', 'ZH': 'Z',
        'H': 'jp', 'h': '',
    },
    'GE': {
        'al': 'aa', 'etu': 'ax', 'e': 'ae', 'ae': 'aeae', 'el': 'ee', 'i': 'ip',
        'il': 'ii', 'o': 'oc', 'ol': 'oo', 'oe': 'ole', 'oel': 'oeoe',
        'u': 'vst', 'ul': 'uu', 'ue': 'uep', 'uel': 'ueue', 'eU': 'oc ip',
        'aI': 'a ip', 'aU': 'a vst', 'r': 'rk',
    },
    'HA': {
        'a_L': 'aa', 'a_S': 'a', 'a_T1': 'a', 'a_T2': 'a', 'a_T3': 'a',
        'e_L': 'ee', 'e_S': 'e', 'e_T1': 'e', 'e_T2': 'e', 'e_T3': 'e',
        'i_L': 'ii', 'i_S': 'i', 'i_T1': 'i', 'i_T2': 'i', 'i_T3': 'i',
        'o_L': 'oo', 'o_S': 'o', 'o_T1': 'o', 'o_T2': 'o', 'o_T3': 'o',
        'u_L': 'uu', 'u_S': 'u', 'u_T1': 'u', 'u_T2': 'u', 'u_T3': 'u',
        'D': 'Dv', 'DZ': 'dZ', 'TS': 'ts', 'K': 'kes', 'KR': 'ces', 'R': 'rrf',
    },
    'JA': {
        'Wl': 'WW', 'ab': 'a', 'abl': 'aa', 'el': 'ee', 'il': 'ii', 'ol': 'oo',
    },
    'KO': {
        'A': 'a', 'AE': 'ae', 'E': 'e', 'EO': 'ov', 'EU': 'W', 'I': 'i',
        'O': 'o', 'OE': 'w e', 'U': 'u', 'UE': 'w ae', 'euI': 'W i',
        'iA': 'j a', 'iE': 'j e', 'iEO': 'j ov', 'iO': 'j o', 'iU': 'j u',
        'oA': 'w a', 'uEO': 'w ov',
        'B': 'b', 'BB': 'p', 'Ph': 'ph', 'G': 'g', 'GG': 'k', 'Kh': 'kh',
        'D': 'd', 'DD': 't', 'Th': 'th', 'J': 'dzp', 'JJ': 'tcp', 'CHh': 'tcph',
        'H': 'h', 'L': 'l', 'M': 'm', 'N': 'n', 'NG': 'ng', 'R': 'rf',
        'S': 'z', 'SS': 's',
    },
    'MA': {
        'b': 'p', 'd': 't', 'g': 'k', 'p': 'ph', 't': 'th', 'r': '9r',
        'h': 'x', 'c': 'tsh', 'ch': 'trsrh', 'j': 'tcp', 'q': 'tcph',
        'sh': 'sr', 'z': 'ts', 'zh': 'trsr',
        'a1': 'a', 'a2': 'a', 'a3': 'a', 'a4': 'a', 'a5': 'a',
        'ai1': 'a i', 'ai2': 'a i', 'ai3': 'a i', 'ai4': 'a i', 'ai5': 'a i',
        'ao1': 'a u', 'ao2': 'a u', 'ao3': 'a u', 'ao4': 'a u', 'ao5': 'a u',
        'e1': 'Y', 'e2': 'Y', 'e3': 'Y', 'e4': 'Y', 'e5': 'Y',
        'ei1': 'e i', 'ei2': 'e i', 'ei3': 'e i', 'ei4': 'e i', 'ei5': 'e i',
        'i1': 'i', 'i2': 'i', 'i3': 'i', 'i4': 'i', 'i5': 'i',
        'ia1': 'j a', 'ia2': 'j a', 'ia3': 'j a', 'ia4': 'j a', 'ia5': 'j a',
        'iao1': 'j a u', 'iao2': 'j a u', 'iao3': 'j a u', 'iao4': 'j a u', 'iao5': 'j a u',
        'ie1': 'j e', 'ie2': 'j e', 'ie3': 'j e', 'ie4': 'j e', 'ie5': 'j e',
        'ii1': 'i', 'ii2': 'i', 'ii3': 'i', 'ii4': 'i', 'ii5': 'i',
        'io1': 'j vst', 'io2': 'j vst', 'io3': 'j vst', 'io4': 'j vst', 'io5': 'j vst',
        'iou1': 'j o u', 'iou2': 'j o u', 'iou3': 'j o u', 'iou4': 'j o u', 'iou5': 'j o u',
        'iu1': 'j o u', 'iu2': 'j o u', 'iu3': 'j o u', 'iu4': 'j o u', 'iu5': 'j o u',
        'o1': 'vst', 'o2': 'vst', 'o3': 'vst', 'o4': 'vst', 'o5': 'vst',
        'ou1': 'o u', 'ou2': 'o u', 'ou3': 'o u', 'ou4': 'o u', 'ou5': 'o u',
        'u1': 'u', 'u2': 'u', 'u3': 'u', 'u4': 'u', 'u5': 'u',
        'ua1': 'w a', 'ua2': 'w a', 'ua3': 'w a', 'ua4': 'w a', 'ua5': 'w a',
        'uai1': 'w a i', 'uai2': 'w a i', 'uai3': 'w a i', 'uai4': 'w a i', 'uai5': 'w a i',
        'ue1': 'w e', 'ue2': 'w e', 'ue3': 'w e', 'ue4': 'w e', 'ue5': 'w e',
        'uei1': 'w e i', 'uei2': 'w e i', 'uei3': 'w e i', 'uei4': 'w e i', 'uei5': 'w e i',
        'uo1': 'w o', 'uo2': 'w o', 'uo3': 'w o', 'uo4': 'w o', 'uo5': 'w o',
        'v1': 'ue', 'v2': 'ue', 'v3': 'ue', 'v4': 'ue', 'v5': 'ue',
        'va1': 'jp a', 'va2': 'jp a', 'va3': 'jp a', 'va4': 'jp a', 'va5': 'jp a',
        've1': 'jp e', 've2': 'jp e', 've3': 'jp e', 've4': 'jp e', 've5': 'jp e',
    },
    'PL': {
        'S': 'sr', 'Z': 'zr', 'sj': 'cp', 'zj': 'zp', 'tS': 'trsr', 'tsj': 'tcp',
        'dZ': 'drzr', 'dz': 'dz', 'dzj': 'dzp', 'c': 'ts', 'h': 'x', 'n~': 'nj',
        'eo5': 'aen', 'oc5': 'ocn', 'e': 'ae', 'o': 'oc',
    },
    'PO': {
        'A': 'a', 'A+': 'a', 'A~': 'atun', 'A~+': 'atun', 'AX': 'atu',
        'E': 'e', 'E+': 'e', 'E~': 'en', 'E~+': 'en',
        'I': 'i', 'I+': 'i', 'I~': 'ipn', 'I~+': 'ipn', 'IX': 'ip',
        'O': 'o', 'O+': 'o', 'O~': 'on', 'O~+': 'on',
        'U': 'u', 'U+': 'u', 'U~': 'un', 'U~+': 'un', 'UX': 'vst',
        'W': 'u', 'W~': 'un',
        'B': 'b', 'D': 'd', 'DJ': 'dj', 'F': 'f', 'G': 'g', 'K': 'k',
        'L': 'l', 'LJ': 'L', 'M': 'm', 'N': 'n', 'NJ': 'nj', 'P': 'p',
        'R': 'r', 'RR': 'rk', 'S': 's', 'SCH': 'S', 'T': 't', 'TJ': 'tj',
        'V': 'v',
    },
    'RU': {
        'ya': 'j a', 'ye': 'j e', 'yo': 'j o', 'yu': 'j u',
        'b~': 'bj', 'd~': 'dj', 'f~': 'fj', 'l~': 'lj', 'm~': 'mj', 'n~': 'nJ',
        'p~': 'pj', 'r~': 'rj', 's~': 'sj', 't~': 'tj', 'w~': 'vj', 'z~': 'zj',
        'jscH': 'zr', 'jscH~': 'zp', 'sch': 'cp', 'sch~': 'cp',
        'tscH': 'tcp', 'tscH~': 'tcp', 'schTsch': 'cp tcp', 'schTsch~': 'cp tcp',
        'h': 'x', 'w': 'v', 'Q': '',
    },
    'SA': {
        'a': 'ab', 'e': 'ae', 'o': 'oc',
        'b': 'B', 'ch': 'tS', 'd': 'Dv', 'dh': 'D', 'g': 'gv', 'gh': 'G',
        'j': 'Jv', 'kh': 'x', 'mb': 'm b', 'mv': 'm v', 'nd': 'n d',
        'ng': 'ng g', 'ng~': 'ng', 'nj': 'nj J', 'ny': 'nj', 'nz': 'n z',
        'r': 'rf', 'sh': 'S', 'th': 'T', 'y': 'j',
    },
    'SP': {
        'a+': 'a', 'e+': 'e', 'i+': 'i', 'o+': 'o', 'u+': 'u', 'n~': 'nj',
    },
    'SW': {
        'al': 'aa', 'abl': 'abab', 'ael': 'aeae', 'alel': 'aleale', 'el': 'ee',
        'i': 'ip', 'il': 'ii', 'ol': 'oo', 'oel': 'oeoe', 'olel': 'oleole',
        'uel': 'ueue', 'ul': 'uu', 'uxl': 'uxux',
        'C': 'sx', 'S': 'cp', 'ks': 'k s', 'r': 'rtu',
    },
    'TH': {
        'c': 'tcp', 'ch': 'tcph', 'kw': 'k w', 'khw': 'kh w', 'r': 'rf', 'z': 'Q',
        'v': 'W', 'vv': 'WW', 'q': 'Y', 'qq': 'YY', 'x': 'ae', 'xx': 'aeae',
        'y': 'oc', 'yy': 'ococ', 'iia': 'i a', 'uua': 'u a', 'vva': 'W a',
        'a0': 'a', 'a1': 'a', 'a2': 'a', 'a3': 'a', 'a4': 'a',
        'aa0': 'aa', 'aa1': 'aa', 'aa2': 'aa', 'aa3': 'aa', 'aa4': 'aa',
        'e0': 'e', 'e1': 'e', 'e2': 'e', 'e3': 'e', 'e4': 'e',
        'ee0': 'ee', 'ee1': 'ee', 'ee2': 'ee', 'ee3': 'ee', 'ee4': 'ee',
        'i0': 'i', 'i1': 'i', 'i2': 'i', 'i3': 'i', 'i4': 'i',
        'ii0': 'ii', 'ii1': 'ii', 'ii2': 'ii', 'ii3': 'ii', 'ii4': 'ii',
        'iia0': 'i a', 'iia1': 'i a', 'iia2': 'i a', 'iia3': 'i a', 'iia4': 'i a',
        'o0': 'o', 'o1': 'o', 'o2': 'o', 'o3': 'o', 'o4': 'o',
        'oo0': 'oo', 'oo1': 'oo', 'oo2': 'oo', 'oo3': 'oo', 'oo4': 'oo',
        'q0': 'Y', 'q1': 'Y', 'q2': 'Y', 'q3': 'Y', 'q4': 'Y',
        'qq0': 'YY', 'qq1': 'YY', 'qq2': 'YY', 'qq3': 'YY', 'qq4': 'YY',
        'u0': 'u', 'u1': 'u', 'u2': 'u', 'u3': 'u', 'u4': 'u',
        'uu0': 'uu', 'uu1': 'uu', 'uu2': 'uu', 'uu3': 'uu', 'uu4': 'uu',
        'uua0': 'u a', 'uua1': 'u a', 'uua2': 'u a', 'uua3': 'u a', 'uua4': 'u a',
        'v0': 'W', 'v1': 'W', 'v2': 'W', 'v3': 'W', 'v4': 'W',
        'vv0': 'WW', 'vv1': 'WW', 'vv2': 'WW', 'vv3': 'WW', 'vv4': 'WW',
        'vva0': 'W a', 'vva1': 'W a', 'vva2': 'W a', 'vva3': 'W a', 'vva4': 'W a',
        'x0': 'ae', 'x1': 'ae', 'x2': 'ae', 'x3': 'ae', 'x4': 'ae',
        'xx0': 'aeae', 'xx1': 'aeae', 'xx2': 'aeae', 'xx3': 'aeae', 'xx4': 'aeae',
        'y0': 'oc', 'y1': 'oc', 'y2': 'oc', 'y3': 'oc', 'y4': 'oc',
        'yy0': 'ococ', 'yy1': 'ococ', 'yy2': 'ococ', 'yy3': 'ococ', 'yy4': 'ococ',
    },
    'TU': {
        'i2': 'W', 'sft': 'j4', 'r': 'rf', 'oe': 'ole',
    },
    'UK': {
        'a': 'ab', 'e': 'ae', 'y': 'ip', 'o': 'oc',
        'dzh': 'dZ', 'h': 'hv', 'sh': 'S', 'tsh': 'tS', 'w': 'vp', 'zh': 'Z',
        'nj': 'nJ', 'hj': 'hvj', 'shj': 'Sj', 'tshj': 'tSj', 'wj': 'vpj', 'zhj': 'Zj',
    },
    'VI': {
        'ch': 'tcp', 'B': 'bv', 'd2': 'Dv', 'd1': 'J', 'ph': 'f', 'x': 's',
        's': 'sr', 'kh': 'x', 'r': 'zr', 'g': 'G', 'nh': 'nj',
        'u2': 'i2', 'u1': 'u', 'e2': 'e', 'e1': 'ae', 'a3': 'ax', 'o3': 'axax',
        'o2': 'o', 'o1': 'oc', 'a1': 'a', 'a2': 'aa',
        'ui': 'u i', 'ui2': 'i2 i', 'ay': 'a i', 'ay3': 'ax i', 'oi': 'oc i',
        'oi2': 'o i', 'oi3': 'axax i', 'oe': 'axax vst', 'ao': 'aa vst',
        'ai': 'aa i', 'iu': 'i vst', 'eo': 'ae vst', 'eu': 'e vst', 'uu2': 'i2 vst',
        'au': 'a vst', 'au3': 'ax vst', 'ie3': 'i ax', 'ua2': 'i2 ax', 'ua': 'u ax',
        'uy': 'uu i', 'uoi2': 'u ax i', 'ieu': 'i ax vst', 'uou': 'i2 ax vst',
        'ie2': 'i ax', 'uoi3': 'i2 ax i', 'oa': 'w a',
    },
}
