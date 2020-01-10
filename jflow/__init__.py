#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jflow."""

import collections
import itertools as itt


class Error(Exception):
    '''Base class for errors in the module.'''


Strip = collections.namedtuple('Strip', ['s', 'ok'])


def strip_suffix(suffix, s):
    if suffix and s.endswith(suffix):
        return Strip(s=s[:len(suffix)], ok=True)
    return Strip(s=s, ok=False)


def strip_prefix(prefix, s):
    if s.startswith(prefix):
        return Strip(s=s[len(prefix):], ok=True)
    return Strip(s=s, ok=False)


def iter_output_lines(output):
    if hasattr(output, 'split'):
        return iter(output.splitlines())
    return (strip_suffix('\n', line).s for line in output)


def output_lines(output):
    if hasattr(output, 'split'):
        return output.splitlines()
    return [strip_suffix('\n', line).s for line in output]


def mark_first(it):
    return itt.zip_longest(it, [True], fillvalue=False)


def as_dict(obj):
    def get_dict():
        try:
            return obj.__dict__
        except AttributeError:
            raise TypeError

    try:
        f = obj.as_dict
    except AttributeError:
        f = get_dict
    return f()
