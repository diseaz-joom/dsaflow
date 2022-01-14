#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Sync from origin."""

import logging
import re

from dsapy import app

from jflow import branch
from jflow import config
from jflow import git
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class SyncMixin(branch.TreeBuilder, run.Cmd):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--with-green',
            action='store_true',
            help='Update tested/develop locally',
        )

    def sync(self):
        current_branch = self.git_current_ref(short=True)

        refs = {r.ref:r for r in self.for_each_ref()}
        # branches = {r.name:r for r in refs.values() if r.fmt == 'branch'}
        remotes = {r.remote + '/' + r.name:r for r in refs.values() if r.fmt == 'remote'}

        self.cmd_action(['git', 'fetch', '--all', '--prune'])
        self.cmd_action(['git', 'checkout', '--detach', 'HEAD'])
        if 'origin/develop' in remotes:
            self.cmd_action(['git', 'branch', '--force', 'develop', 'origin/develop'])
        if 'origin/master' in remotes:
            self.cmd_action(['git', 'branch', '--force', 'master', 'origin/master'])
        if 'origin/tested/develop' in remotes:
            self.cmd_action(['git', 'branch', '--force', 'tested/develop', 'origin/tested/develop'])
        self.cmd_action(['git', 'checkout', current_branch])
        if self.flags.with_green:
            self.cmd_action(['green-develop-update'])
