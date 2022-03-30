#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Remove a branch."""

import logging
import pprint
import re

from dsapy import app

import jflow
from jflow import branch
from jflow import common
from jflow import config
from jflow import git
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class DeleteCmd(branch.TreeBuilder, app.Command):
    '''Remove a branch and all related branches.'''
    name='delete'

    DRY_RUN = True

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'branch',
            nargs='+',
            help='Branch to remove',
        )

    def main(self):
        self.git_check_workdir_is_clean()

        current_ref = self.git_current_ref(short=True)

        tree_branches = {}
        branches = self.branch_tree()
        for arg_branch in self.flags.branch:
            if arg_branch == current_ref:
                raise Error('Cannot delete current branch')
            for b in branches.values():
                if b.name == arg_branch:
                    tree_branches[arg_branch] = b
                    break
            if arg_branch not in tree_branches:
                raise Error('Branch %r not found', arg_branch)

        for arg_branch in self.flags.branch:
            cb = tree_branches[arg_branch]

            if cb.jflow:
                self.cmd_action(['git', 'config', '--remove-section', config.branch_key_base(cb.name)])

                if cb.debug:
                    self.cmd_action(['git', 'push', 'origin', ':{b.name}'.format(b=cb.debug)])

                if cb.remote:
                    self.cmd_action(['git', 'push', 'origin', ':{b.name}'.format(b=cb.remote)])

                if cb.public:
                    self.cmd_action(['git', 'branch', '--delete', '--force', cb.public.name])

                if cb.stgit:
                    self.cmd_action(['stg', 'branch', '--delete', '--force', cb.name])
                else:
                    self.cmd_action(['git', 'branch', '--delete', '--force', cb.name])
            else:
                if cb.stgit:
                    self.cmd_action(['stg', 'branch', '--delete', '--force', cb.name])
                else:
                    self.cmd_action(['git', 'branch', '--delete', '--force', cb.name])
