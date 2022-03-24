#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import argparse
import locale
import logging
import shlex
import subprocess
from typing import *

from dsapy import app
from dsapy import flag


_logger = logging.getLogger(__name__)

ENCODING: str = locale.getpreferredencoding()
FULL_RUN = False


@flag.argroup('glow.run')
def _options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '-n', '--dry-run',
        action='store_false',
        dest='full_run',
        default=FULL_RUN,
        help='Do not make any changes.',
    )
    parser.add_argument(
        '-f', '--full-run',
        action='store_true',
        dest='full_run',
        default=FULL_RUN,
        help='Force changes.'
    )


class _globals(object):
    full_run = FULL_RUN


@app.onmain
def _globals_from_flags(**kwargs: Any) -> app.KwArgsGenerator:
    _globals.full_run = kwargs['flags'].full_run
    yield kwargs


def full_run() -> bool:
    return _globals.full_run


def read(args: List[str], force=True, check=True, encoding=ENCODING, universal_newlines=True, **kwargs) -> Sequence[str]:
    p = run(args, force=force, check=check, stdout=subprocess.PIPE, encoding=encoding, universal_newlines=universal_newlines, **kwargs)
    if p.stdout is None:
        return []
    return _output_lines(p.stdout)


def run(args: List[str], force=False, check=True, stdout=None, encoding=ENCODING, universal_newlines=True, **kwargs) -> subprocess.CompletedProcess:
    run = force or _globals.full_run
    run_str = 'yes' if run else 'skip'
    _logger.info('Run[%s]: %s', run_str, ' '.join(shlex.quote(s) for s in args))
    if run:
        return subprocess.run(args, encoding=encoding, stdout=stdout, check=check, universal_newlines=universal_newlines, **kwargs)
    return subprocess.CompletedProcess(args, 0)


def run_pipe(cmds: List[List[str]], force=False, stdout=None, encoding=ENCODING, check=True, universal_newlines=True, **kwargs):
    run = force or _globals.full_run
    run_str = 'yes' if run else 'skip'
    _logger.info('Run[%s]: %s', run_str, ' | '.join(' '.join(shlex.quote(s) for s in args) for args in cmds))

    if run:
        last_i = len(cmds) - 1
        proc = None
        stdin = None
        for args in cmds[:-1]:
            proc = subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE)
            stdin = proc.stdout
        args = cmds[-1]
        return subprocess.run(args, stdin=stdin, stdout=stdout, encoding=ENCODING, check=check, universal_newlines=universal_newlines, **kwargs)
    return subprocess.CompletedProcess(cmds[-1], 0)


def _output_lines(output: str) -> List[str]:
    return output.splitlines()
    # return [line.rstrip('\n') for line in output]
