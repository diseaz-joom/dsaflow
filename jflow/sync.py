#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Sync from origin."""

import logging
import re

from dsapy import app

from jflow import config
from jflow import git
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class SyncMixin(git.Git, run.Cmd):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--no-green',
            action='store_true',
            help='Do not update green-develop branch',
        )

    def sync(self):
        current_branch = self.git_current_ref(short=True)

        self.cmd_action(['git', 'fetch', '--all', '--prune'])
        self.cmd_action(['git', 'checkout', '--detach', 'HEAD'])
        self.cmd_action(['git', 'branch', '--force', 'develop', 'origin/develop'])
        self.cmd_action(['git', 'branch', '--force', 'master', 'origin/master'])
        self.cmd_action(['git', 'checkout', current_branch])
        if not self.flags.no_green:
            self.cmd_action(['green-develop-update'])
