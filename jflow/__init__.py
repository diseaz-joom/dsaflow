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


def ensure_suffix(suffix, s):
    if s.endswith(suffix):
        return Strip(s=s, ok=True)
    return Strip(s=s + suffix, ok=False)


def ensure_prefix(prefix, s):
    if s.startswith(prefix):
        return Strip(s=s, ok=True)
    return Strip(s=prefix + s, ok=False)


def iter_output_lines(output):
    if hasattr(output, 'split'):
        return iter(output.splitlines())
    return (strip_suffix('\n', line).s for line in output)


def output_lines(output):
    if hasattr(output, 'splitlines'):
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


def lazy_value(factory):
    def gen():
        v = factory()
        while True:
            yield v
    return gen().__next__


def lazy_default(v, factory):
    if v is None:
        return lazy_value(factory)
    return lambda: v
