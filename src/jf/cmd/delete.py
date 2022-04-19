#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Remove a branch."""

from typing import List, Optional, Sequence

import logging

import click

from jf import branch
from jf import command
from jf import git
from jf import repo
from jf.cmd import root


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


@root.group.command()
@click.option('--merged', type=click.Choice(('U', 'F', 'D', 'M')),
              help='Remove all branches with this status or greater. Status ordering U->F->D->M.')
@click.argument('branch', nargs=-1)
def delete(branch: Sequence[str], merged: str):
    '''Remove a branch and all related branches.'''
    gc = repo.Cache()

    input_branches = set(branch)
    if merged:
        for b in gc.branches.values():
            if not Filter(gc, b).is_merge_status(merged):
                continue
            input_branches.add(b.name)

    bs: List[repo.Branch] = []
    for arg in input_branches:
        if arg not in gc.branch_by_abbrev:
            raise Error(f'Branch {arg!r} not found')
        b = gc.branch_by_abbrev[arg]
        if b.name == git.current_branch:
            _logger.error('Cannot delete current branch')
            continue
        if b.protected:
            _logger.error(f'Branch {b.name!r} is protected')
            continue
        bs.append(b)

    for b in bs:
        if b.jflow_version:
            refs_list = [b.public_resolved, b.ldebug_resolved, b.review_resolved, b.debug_resolved]
            refs = {r for r in refs_list if r and r != b.ref}
            for r in refs:
                _remove_ref(r)
            _remove_branch(b)

            command.run(['git', 'config', '--remove-section', gc.cfg.branch[b.name].jf.path])
        else:
            _remove_branch(b)


def _remove_ref(ref: Optional[git.RefName]) -> None:
    if not ref or not ref.branch:
        return
    if ref.is_remote:
        if not ref.remote:
            raise Error(f'No remote for remote ref {ref!r}')
        command.run(['git', 'push', ref.remote, f':{ref.branch}'])
    else:
        command.run(['git', 'branch', '--delete', '--force', ref.branch])


def _remove_branch(b: branch.Generic) -> None:
    if b.is_stgit:
        command.run(['stg', 'branch', '--delete', '--force', b.name])
    else:
        command.run(['git', 'branch', '--delete', '--force', b.name])


class Filter:
    def __init__(self, gc: repo.Cache, b: repo.Branch) -> None:
        self.gc = gc
        self.b = b

    def is_merged_into(self, r: Optional[git.Ref]) -> bool:
        return bool(r and r.is_valid and self.gc.is_merged_into(self.b.sha, r.sha))

    def is_merge_status(self, status: str) -> bool:
        all_stats = 'MDFU'
        sts = ''
        if 'master' in self.gc.refs and self.is_merged_into(self.gc.refs[git.RefName('master')]):
            sts = all_stats
        elif 'develop' in self.gc.refs and self.is_merged_into(self.gc.refs[git.RefName('develop')]):
            sts = all_stats[1:]
        elif self.is_merged_into(self.b.fork_resolved):
            sts = all_stats[2:]
        elif self.is_merged_into(self.b.upstream_resolved):
            sts = all_stats[3:]
        return status in sts
