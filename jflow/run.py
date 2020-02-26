#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Commons for jflow."""

import locale
import logging
import shlex
import subprocess

from dsapy import app

import jflow

_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


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
        parser.add_argument(
            '-f', '--force',
            action='store_false',
            dest='dry_run',
            default=cls.DRY_RUN,
            help='Force changes.'
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
