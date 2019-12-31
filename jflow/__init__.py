#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jflow."""

import itertools as itt


class Error(Exception):
    '''Base class for errors in the module.'''


def strip_suffix(suffix, s):
    if suffix and s.endswith(suffix):
        return s[:len(suffix)]
    return s


def iter_output_lines(output):
    if hasattr(output, 'split'):
        return iter(output.splitlines())
    return (strip_suffix('\n', line) for line in output)


def output_lines(output):
    if hasattr(output, 'split'):
        return output.splitlines()
    return [strip_suffix('\n', line) for line in output]


def mark_first(it):
    return itt.zip_longest(it, [True], fillvalue=False)
