#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Sync from remote."""

import logging
import re

from dsapy import app

from jf import command
from jf import config
from jf import git
from jf import green


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Mixin(green.Mixin, app.Command):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--with-green',
            action='store_true',
            help='Update tested branch locally',
        )

    def sync(self):
        git.check_workdir_is_clean()

        with git.detach_head():
            command.run(['git', 'fetch', '--all', '--prune'])

            gc = git.Cache()
            for b in gc.branches.values():
                if not gc.cfg.branch(b.name).jf().sync().get_bool():
                    continue
                upstream = b.upstream
                if not upstream:
                    continue
                upstream_sha = upstream.sha
                b_ref = b.ref
                b_sha = b_ref.sha
                b_commit = gc.commits[b_sha]
                if gc.commits[upstream_sha].is_merged_into(gc, b_commit):
                    return
                command.run(['git', 'branch', '--force', b.name, upstream.name])

            if self.flags.with_green:
                for b in gc.branches.values():
                    if b.tested_branch_name:
                        self.green(gc, b)
