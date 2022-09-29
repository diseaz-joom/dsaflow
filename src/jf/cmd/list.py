#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import functools
import typing as t

import click

from jf import color
from jf import git
from jf import repo
from jf.cmd import root


class Error(Exception):
    '''Base for errors in the module.'''


class ListLine:
    DEVELOP_REF = git.RefName('develop')
    MASTER_REF = git.RefName('master')

    def __init__(self, gc: repo.Cache, b: repo.Branch, maxlen: int = None):
        self.gc = gc
        self.b = b
        self.maxlen = maxlen
        self.merged

    @property
    def current(self) -> str:
        if self.b.ref == git.current_ref:
            return '>'
        return ' '

    @property
    def typ(self) -> str:
        if self.b.is_jflow:
            return 'j'
        if self.b.is_stgit:
            return 's'
        return '.'

    @property
    def debug(self) -> str:
        if self.b.debug_resolved and self.b.ref != self.b.debug_resolved:
            return 'D'
        if self.b.ldebug_resolved and self.b.ref != self.b.ldebug_resolved:
            return 'd'
        return '.'

    @property
    def review(self) -> str:
        if self.b.review_resolved and self.b.ref != self.b.review_resolved:
            return 'R'
        if self.b.public_resolved and self.b.ref != self.b.public_resolved:
            return 'r'
        return '.'

    @property
    def merged(self) -> str:
        r = '.'
        if self.b.upstream_resolved and self.is_merged_into(self.b.upstream_resolved):
            r = 'U'
        develop_ref = self.gc.refs.get(self.DEVELOP_REF, None)
        if self.b.ref != develop_ref and self.is_merged_into(develop_ref):
            r = 'D'
        if self.b.fork_resolved and self.b.fork_resolved != self.b.upstream_resolved and self.is_merged_into(self.b.fork_resolved):
            r = 'F'
        master_ref = self.gc.refs.get(self.MASTER_REF, None)
        if self.b.ref != master_ref and self.is_merged_into(master_ref):
            r = 'M'
        return r

    @property
    def name_pad(self) -> str:
        if not self.maxlen:
            return ''
        pad = self.maxlen - len(self.b.name)
        if pad < 0:
            return ''
        return ' ' * pad

    @property
    def description(self) -> str:
        if not self.b.description:
            return ''
        return ' | ' + self.b.description

    @property
    def jflow(self) -> str:
        return 'j' if self.b.is_jflow else '.'

    @property
    def stgit(self) -> str:
        return 's' if self.b.is_stgit else '.'

    @functools.lru_cache(maxsize=None)
    def is_merged_into(self, m: t.Optional[git.Ref]) -> bool:
        return bool(m and m.is_valid and self.gc.is_merged_into(self.b.sha, m.sha))

    @property
    def public(self) -> str:
        if self.b.public_resolved:
            return 'p'
        return '.'


@root.group.command('list')
@click.option('-a', '--all', is_flag=True, default=False,
              help='Show all branches, including hidden')
def list_cmd(all):
    '''List branches.'''

    gc = repo.Cache()

    branches = list(gc.branches.values())
    maxlen = max(len(b.name) for b in branches)
    lines = [ListLine(gc, b, maxlen=maxlen) for b in branches if all or not b.hidden]
    print('''
 +------- 'j' = controlled by jflow; 's' = controlled by StGit
 |+------ 'd' = has local debug branch; 'D' = has remote debug
 ||+----- 'r' = has local review branch; 'R' = has remote review
 |||+---- merged into: 'U' = upstream; 'F' = fork; 'D' = develop; 'M' = master
 ||||'''.lstrip('\n'))
    for line in lines:
        print('{i.current}{i.typ}{i.debug}{i.review}{i.merged} {c.W}{i.b.name}{c.N}{i.name_pad}{i.description}'.format(
            i=line, c=color.Colors,
        ))
