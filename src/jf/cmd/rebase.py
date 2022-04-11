#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Rebase branch to a fresh tip."""

from typing import Optional

import logging

from dsapy import app

from jf import command
from jf import git


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
    def clean(self) -> None:
        command.run_pipe([
            ['git', 'ls-files', '--others', '--directory', '--exclude-standard'],
            ['xargs', 'rm', '--recursive', '--force', '--verbose'],
        ])


class Clean(CleanMixin, app.Command):
    '''Clean garbage files after rebase.'''

    name = 'clean'

    def main(self) -> None:
        self.clean()


class Rebase(CleanMixin, app.Command):
    '''Rebase a branch.'''
    name = 'rebase'

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
            '--fork',
            metavar='BRANCH',
            help='Use this branch as `fork` parameter',
        )

    def main(self) -> None:
        git.check_workdir_is_clean()

        gc = git.Cache()

        branch_name = git.current_branch
        if not branch_name:
            raise Error('HEAD is not a branch')
        branch = gc.branches[branch_name]

        if not branch.is_jflow:
            raise NotImplementedError('Rebase for non-jflow branches is not implemented yet.')
        if not branch.is_stgit:
            raise NotImplementedError('Rebase for non-StGit branches is not implemented yet.')

        if branch.jflow_version != 1:
            raise UnsupportedJflowVersionError(branch.jflow_version)

        need_publish = bool(branch.public)
        if need_publish:
            branch.publish_local_public(msg=self.flags.message)

        base_ref: Optional[git.Ref] = None

        if self.flags.fork:
            base_ref = gc.get_ref(self.flags.fork)
            if base_ref.kind != git.Kind.head:
                raise Error(f'Not a local branch: {base_ref.name!r}')
        else:
            fork_ref = branch.fork
            if fork_ref:
                if fork_ref.kind == git.Kind.head:
                    base_ref = fork_ref
                else:
                    _logger.warning(f'Fork ref {fork_ref.name!r} is not a branch')
            if not base_ref:
                upstream_ref = branch.upstream
                if upstream_ref:
                    if upstream_ref.kind == git.Kind.head:
                        base_ref = upstream_ref
                    else:
                        _logger.warning(f'Upstream ref {upstream_ref.name!r} is not a branch')

        if not base_ref:
            raise Error('What to rebase on?')

        command.run(['stg', 'rebase', '--merged', base_ref.name])
        command.run(['git', 'clean', '-d', '--force'])
        self.clean()

        if need_publish:
            branch.publish_local_public(msg=f'Merge {base_ref.branch_name} into {branch.name}')
