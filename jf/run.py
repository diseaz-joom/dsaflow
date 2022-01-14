#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jflow."""

import locale
import logging
import selectors
import shlex
import subprocess

from jf import common
from jf import struct


_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


class _RunnerFlags(object):
    RUNNER_DRY_RUN = False

    def runner_options(self):
        return RunnerOptions(dry_run=self.flags.dry_run)


class RunnerFlagsDryRun(_RunnerFlags):
    '''Runner options from flags.'''

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-n', '--dry-run',
            action='store_true',
            default=cls.RUNNER_DRY_RUN,
            help=('Do not make any changes.'
                  ' Commands to be executed will be logged.'),
        )


class RunnerFlagsForce(_RunnerFlags):
    '''Runner options from flags.'''

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-f', '--force',
            action='store_false',
            dest='dry_run',
            default=cls.RUNNER_DRY_RUN,
            help='Force changes.',
        )


class RunnerOptions(object):
    def __init__(self, dry_run=False):
        self.dry_run = dry_run


class Runner(object):
    def __init__(self, options):
        self.options = options

    def cmd_output(self, args):
        return self.cmd_output_ret(args)[0]

    def run_command(self, cmd, input=None, timeout=10):
        if input is not None:
            p = subprocess.Popen(
                cmd,
                encoding=_encoding, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True,
            )
            output, _ = p.communicate(input=input, timeout=timeout)
            return common.output_lines(output)

        p = subprocess.run(args, encoding=_encoding, stdin=stdin, stdout=subprocess.PIPE, universal_newlines=True)

        _logger.info('Run[yes]: %s', ' '.join(shlex.quote(s) for s in args))
        p = subprocess.run(args, encoding=_encoding, stdout=subprocess.PIPE, check=check, universal_newlines=True)
        return jflow.output_lines(p.stdout), p.returncode

class Cmd(object):
    '''Command runner.'''

    DRY_RUN = False

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-n', '--dry-run',
            action='store_true',
            default=cls.DRY_RUN,
            help=('Do not make any changes.'
                  ' Commands to be executed will be logged.'),
        )

    def cmd_output(self, args):
        return self.cmd_output_ret(args)[0]

    def cmd_output_ret(self, args, check=True):
        _logger.info('Run[yes]: %s', ' '.join(shlex.quote(s) for s in args))
        p = subprocess.run(args, encoding=_encoding, stdout=subprocess.PIPE, check=check, universal_newlines=True)
        return jflow.output_lines(p.stdout), p.returncode

    def cmd_action(self, args, check=True):
        run_str = 'dry' if self.flags.dry_run else 'yes'
        _logger.info('Run[%s]: %s', run_str, ' '.join(shlex.quote(s) for s in args))
        if self.flags.dry_run:
            return 0
        p = subprocess.run(args, encoding=_encoding, check=check, universal_newlines=True)
        return p.returncode

    def cmd_action_pipe(self, cmds):
        run_str = 'dry' if self.flags.dry_run else 'yes'
        cmdq = ' | '.join(
            ' '.join(shlex.quote(s) for s in args)
            for args in cmds
        )
        _logger.info('Run[%s]: %s', run_str, cmdq)
        if self.flags.dry_run:
            return 0
        proc = None
        pipe_out = None
        for args, m in IterWithMarks(cmds):
            stdout = None if m.last else subprocess.PIPE
            last_args = args
            proc = subprocess.Popen(args, encoding=_encoding, stdin=pipe_out, stdout=stdout, universal_newlines=True)
            pipe_out = None if m.last else proc.stdout
        if proc is None:
            return 0
        retcode = proc.wait()
        if retcode:
            raise subprocess.CalledProcessError(retcode, args)


class IterMarks(object):
    def __init__(self, index=0, last=False):
        self.index = index
        self.last = last


class IterWithMarks(object):
    def __init__(self, it):
        self._it = iter(it)
        self._next, self._eoi = self._get_next()
        self._i = 0

    def _get_next(self):
        n, e = None, True
        for v in self._it:
            n, e = v, False
            break
        return n, e

    def __iter__(self):
        return self

    def __next__(self):
        if self._eoi:
            raise StopIteration
        v, i = self._next, self._i
        self._i += 1
        self._next, self._eoi = self._get_next()
        return v, IterMarks(index=i, last=self._eoi)

def output_lines(output):
    if hasattr(output, 'splitlines'):
        return output.splitlines()
    return [strip_suffix('\n', line).s for line in output]
