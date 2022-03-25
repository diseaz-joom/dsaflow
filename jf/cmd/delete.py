#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Remove a branch."""

from typing import *

import logging
import re

from dsapy import app

from jf import command
from jf import common
from jf import config
from jf import git


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Delete(app.Command):
    '''Remove a branch and all related branches.'''

    name='delete'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--merged',
            choices=('U', 'F', 'D', 'M'),
            metavar='MERGE-STATUS',
            default=None,
            help='Remove all branches with this status or greater. Status ordering U->F->D->M.',
        )
        parser.add_argument(
            'branch',
            nargs='*',
            help='Branch to remove',
        )

    def main(self) -> None:
        gc = git.Cache()

        input_branches = set(self.flags.branch)
        if self.flags.merged:
            for b in gc.branches.values():
                if not Filter(gc, b).is_merge_status(self.flags.merged):
                    continue
                input_branches.add(b.name)

        branches: List[git.Branch] = []
        for arg in input_branches:
            b = gc.branch_by_abbrev.get(arg, None)
            if not b:
                raise Error(f'Branch {arg!r} not found')
            if b.name == git.current_branch:
                _logger.error('Cannot delete current branch')
                continue
            if b.protected:
                _logger.error(f'Branch {b.name!r} is protected')
                continue
            branches.append(b)

        for b in branches:
            if b.jflow_version:
                self.remove_ref(b.debug)
                self.remove_ref(b.review)
                self.remove_ref(b.ldebug)
                self.remove_ref(b.public)
                self.remove_branch(b)

                command.run(['git', 'config', '--remove-section', gc.cfg.branch(b.name).jf.key])
            else:
                self.remove_branch(b)

    def remove_ref(self, ref: Optional[git.RefName]) -> None:
        if not ref or not ref.branch_name:
            return
        if ref.is_remote:
            command.run(['git', 'push', ref.remote, f':{ref.branch_name}'])
        else:
            command.run(['git', 'branch', '--delete', '--force', ref.branch_name])

    def remove_branch(self, b: git.GenericBranch) -> None:
        if b.stgit:
            command.run(['stg', 'branch', '--delete', '--force', b.name])
        else:
            command.run(['git', 'branch', '--delete', '--force', b.name])


class Filter:
    def __init__(self, gc: git.Cache, b: git.Branch) -> None:
        self.gc = gc
        self.b = b

    def is_merged_into(self, r: Optional[git.Ref]) -> bool:
        return bool(r and r.is_valid and self.gc.is_merged_into(self.b.sha, r.sha))

    def is_merge_status(self, status: str) -> bool:
        all_stats = 'MDFU'
        sts = []
        if 'master' in self.gc.refs and self.is_merged_into(self.gc.refs['master']):
            sts = all_stats
        elif 'develop' in self.gc.refs and self.is_merged_into(self.gc.refs['develop']):
            sts = all_stats[1:]
        elif self.is_merged_into(self.b.fork):
            sts = all_stats[2:]
        elif self.is_merged_into(self.b.upstream):
            sts = all_stats[3:]
        return status in sts
