#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Sync from origin."""

import logging
import re

from dsapy import app

from jflow import branch
from jflow import config
from jflow import git
from jflow import green
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class SyncMixin(green.Mixin, branch.TreeBuilder, git.Git, run.Cmd):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--with-green',
            action='store_true',
            help='Update tested/develop locally',
        )

    def sync(self):
        refs = {r.ref:r for r in self.for_each_ref()}
        remotes = {r.remote + '/' + r.name:r for r in refs.values() if r.fmt == 'remote'}

        with self.git_detach_head():
            self.cmd_action(['git', 'fetch', '--all', '--prune'])
            if 'origin/develop' in remotes:
                self.cmd_action(['git', 'branch', '--force', 'develop', 'origin/develop'])
            if 'origin/master' in remotes:
                self.cmd_action(['git', 'branch', '--force', 'master', 'origin/master'])
            if not self.flags.with_green and green.GREEN_DEVELOP_UPSTREAM in remotes:
                self.cmd_action(['git', 'branch', '--force', green.GREEN_DEVELOP, green.GREEN_DEVELOP_UPSTREAM])
            if self.flags.with_green:
                self.green()
