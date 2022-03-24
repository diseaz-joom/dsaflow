#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Rebase branch to a fresh tip."""

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


class NotImplementedError(Error):
    '''Not implemented.'''


class UnsupportedJflowVersionError(Error):
    '''Unsupported Jflow version.'''

    def __init__(self, v):
        return super(f'Unsupported Jflow version: {v}')


class CleanMixin:
    def clean(self):
        command.run_pipe([
            ['git', 'ls-files', '--others', '--directory', '--exclude-standard'],
            ['xargs', 'rm', '--recursive', '--force', '--verbose'],
        ])


class Clean(CleanMixin, app.Command):
    name='clean'

    def main(self):
        self.clean()


class Rebase(CleanMixin, app.Command):
    '''Rebase a branch.'''
    name='rebase'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-m', '--message',
            metavar='MESSAGE',
            default=None,
            help='Message to commit current changes before rebase',
        )
        parser.add_argument(
            '--upstream',
            metavar='BRANCH',
            help='Use this branch as `upstream` parameter',
        )
        parser.add_argument(
            '--fork',
            metavar='BRANCH',
            help='Use this branch as `fork` parameter',
        )

    def main(self):
        git.check_workdir_is_clean()

        gc = git.Cache()

        branch_name = git.current_branch
        if not branch_name:
            raise Error('HEAD is not a branch')
        branch = gc.branches[branch_name]

        need_publish = bool(branch.public)
        if need_publish:
            branch.publish_local_public(msg=self.flags.message)

        upstream_ref = branch.upstream
        if self.flags.upstream:
            upstream_ref = gc.get_ref(self.flags.upstream)
            if upstream_ref.kind != git.Kind.head:
                raise Error(f'Not a local branch: {upstream_ref.name!r}')
        update_upstream = upstream_ref.name != branch.upstream.name
        upstream_branch = gc.branches[upstream_ref.branch_name]

        fork_ref = branch.fork
        if self.flags.fork:
            fork_ref = gc.get_ref(self.flags.fork)
            if fork_ref.kind != git.Kind.head:
                raise Error(f'Not a local branch: {fork_ref.name!r}')
        elif update_upstream:
            upstream_branch = gc.branch_by_ref[upstream_ref.name]
            tested_branch = upstream_branch.tested_branch
            if tested_branch:
                fork_ref = tested_branch.ref
            else:
                fork_ref = upstream_ref
        update_fork = fork_ref.name != branch.fork.name
        fork_branch = gc.branches[fork_ref.branch_name]

        if not branch.is_jflow:
            raise NotImplementedError('Rebase for non-jflow branches is not implemented yet.')
        if not branch.is_stgit:
            raise NotImplementedError('Rebase for non-StGit branches is not implemented yet.')

        if branch.jflow_version != 1:
            raise UnsupportedJflowVersionError(branch.jflow_version)

        if update_upstream:
            gc.cfg.branch(branch.name).jf.upstream.set(upstream_branch.name)
        if update_fork:
            gc.cfg.branch(branch.name).jf.upstream.set(fork_branch.name)

        command.run(['stg', 'rebase', '--merged', fork_ref.name])
        command.run(['git', 'clean', '-d', '--force'])
        self.clean()

        if need_publish:
            branch.publish_local_public(msg=f'Merge {fork_branch.name} into {branch.name}')
