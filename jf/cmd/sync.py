#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Update green-develop."""

import logging

from dsapy import app

from jf import git
from jf import green
from jf import sync


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Green(green.Mixin, app.Command):
    '''Alternatively update tested branch.'''
    name = 'green'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-b', '--branch',
            default='develop',
            help='Branch to operate on.',
        )
        parser.add_argument(
            '-t', '--tested',
            default=None,
            help='Tested branch.',
        )

    def main(self):
        gc = git.Cache()
        self.green(gc, self.flags.branch, self.flags.tested)


class Sync(sync.Mixin, app.Command):
    '''Synchronize from remote.'''
    name = 'sync'

    def main(self):
        self.sync()
