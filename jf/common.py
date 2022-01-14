#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jf."""

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


def ensure_suffix(suffix, s):
    if s.endswith(suffix):
        return Strip(s=s, ok=True)
    return Strip(s=s + suffix, ok=False)


def ensure_prefix(prefix, s):
    if s.startswith(prefix):
        return Strip(s=s, ok=True)
    return Strip(s=prefix + s, ok=False)


def output_lines(output):
    if hasattr(output, 'splitlines'):
        return output.splitlines()
    return [line.rstrip('\r\n') for line in output]
