#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Rebase branch to a fresh tip."""

from typing import Optional

import logging

import click

from jf import command
from jf import git
from jf import repo
from jf.cmd import root


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class NotImplementedError(Error):
    '''Not implemented.'''


class UnsupportedJflowVersionError(Error):
    '''Unsupported Jflow version.'''

    def __init__(self, v):
        return super(f'Unsupported Jflow version: {v}')


@root.group.command()
def clean():
    '''Clean garbage files after rebase.'''

    command.run_pipe([
        ['git', 'ls-files', '--others', '--directory', '--exclude-standard'],
        ['xargs', 'rm', '--recursive', '--force', '--verbose'],
    ])


@root.group.command()
@click.option('-m', '--message',
              help='Message to commit current changes before rebase')
@click.option('--fork',
              help='Use this branch as `fork` parameter')
@click.pass_context
def rebase(ctx: click.Context, message: Optional[str], fork: Optional[str]):
    '''Rebase a branch.'''

    git.check_workdir_is_clean()

    gc = repo.Cache()

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

    need_publish = bool(branch.public_resolved)
    if need_publish:
        branch.publish_local_public(msg=message)

    base_ref: Optional[git.Ref] = None

    if fork:
        base_ref = gc.get_ref(fork)
        if base_ref.kind != git.Kind.head:
            raise Error(f'Not a local branch: {base_ref.name!r}')
    else:
        fork_ref = branch.fork_resolved
        if fork_ref:
            if fork_ref.kind == git.Kind.head:
                base_ref = fork_ref
            else:
                _logger.warning(f'Fork ref {fork_ref.name!r} is not a branch')
        if not base_ref:
            upstream_ref = branch.upstream_resolved
            if upstream_ref:
                if upstream_ref.kind == git.Kind.head:
                    base_ref = upstream_ref
                else:
                    _logger.warning(f'Upstream ref {upstream_ref.name!r} is not a branch')

    if not base_ref:
        raise Error('What to rebase on?')

    command.run(['stg', 'rebase', '--merged', base_ref.name])
    command.run(['git', 'clean', '-d', '--force'])
    ctx.invoke(clean)

    if need_publish:
        branch.publish_local_public(msg=f'Merge {base_ref.branch} into {branch.name}')
