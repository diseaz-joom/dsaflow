#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import typing as t

import locale
import logging
import shlex
import subprocess

import click


_logger = logging.getLogger(__name__)
ENCODING: str = locale.getpreferredencoding()


class _globals(object):
    full_run = True


F = t.TypeVar("F", bound=t.Callable[..., t.Any])
FC = t.TypeVar("FC", bound=t.Union[t.Callable[..., t.Any], click.Command])


def options(f: F) -> F:
    f = click.option('-f/-n', '--full-run/--dry-run', default=_globals.full_run,
                     help='Execute modification commands.')(f)
    return f


def process_options(ctx: click.Context):
    _globals.full_run = ctx.params['full_run']


def full_run() -> bool:
    return _globals.full_run


def read(
        args: t.List[str],
        force=True,
        check=True,
        encoding=ENCODING,
        universal_newlines=True,
        **kwargs,
) -> t.Sequence[str]:
    p = run(
        args,
        force=force,
        check=check,
        stdout=subprocess.PIPE,
        encoding=encoding,
        universal_newlines=universal_newlines,
        **kwargs)
    if p.stdout is None:
        return []
    return _output_lines(p.stdout)


def run(
        args: t.List[str],
        force=False,
        check=True,
        stdout=None,
        encoding=ENCODING,
        universal_newlines=True,
        **kwargs,
) -> subprocess.CompletedProcess:
    run = force or _globals.full_run
    run_str = 'yes' if run else 'skip'
    _logger.debug('Run[%s]: %s', run_str, ' '.join(shlex.quote(s) for s in args))
    if run:
        return subprocess.run(
            args,
            encoding=encoding,
            stdout=stdout,
            check=check,
            universal_newlines=universal_newlines,
            **kwargs)
    return subprocess.CompletedProcess(args, 0)


def run_pipe(
        cmds: t.List[t.List[str]],
        force=False,
        stdout=None,
        encoding=ENCODING,
        check=True,
        universal_newlines=True,
        **kwargs,
) -> subprocess.CompletedProcess:
    run = force or _globals.full_run
    run_str = 'yes' if run else 'skip'
    _logger.debug('Run[%s]: %s', run_str, ' | '.join(' '.join(shlex.quote(s) for s in args) for args in cmds))

    if run:
        proc = None
        stdin = None
        for args in cmds[:-1]:
            proc = subprocess.Popen(args, stdin=stdin, stdout=subprocess.PIPE)
            stdin = proc.stdout
        args = cmds[-1]
        return subprocess.run(
            args,
            stdin=stdin,
            stdout=stdout,
            encoding=ENCODING,
            check=check,
            universal_newlines=universal_newlines,
            **kwargs)
    return subprocess.CompletedProcess(cmds[-1], 0)


def _output_lines(output: str) -> t.List[str]:
    return output.splitlines()
