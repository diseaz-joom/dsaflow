#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jflow."""

import locale
import logging
import subprocess

import jflow

_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


def get_output(args):
    _logger.debug('Run: %r', args)
    p = subprocess.run(args, encoding=_encoding, stdout=subprocess.PIPE, check=True, universal_newlines=True)
    return jflow.output_lines(p.stdout)


def get_output_ret(args, check=True):
    _logger.debug('Run: %r', args)
    p = subprocess.run(args, encoding=_encoding, stdout=subprocess.PIPE, check=check, universal_newlines=True)
    return jflow.output_lines(p.stdout), p.returncode


def action(args, check=True):
    _logger.debug('Run: %r', args)
    p = subprocess.run(args, encoding=_encoding, check=check, universal_newlines=True)
    return p.returncode
