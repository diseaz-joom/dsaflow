#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from jf import common

_colors_dict = {
    'N': '\033[0m',

    'k': '\033[0;30m',
    'r': '\033[0;31m',
    'g': '\033[0;32m',
    'y': '\033[0;33m',
    'b': '\033[0;34m',
    'm': '\033[0;35m',
    'c': '\033[0;36m',
    'w': '\033[0;37m',

    'K': '\033[1;30m',
    'R': '\033[1;31m',
    'G': '\033[1;32m',
    'Y': '\033[1;33m',
    'B': '\033[1;34m',
    'M': '\033[1;35m',
    'C': '\033[1;36m',
    'W': '\033[1;37m',

    'ul': '\033[4m',
}

Colors = common.Struct(_colors_dict)
NoColors = common.Struct({c: '' for c in _colors_dict.keys()})
