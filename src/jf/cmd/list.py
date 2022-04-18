#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import functools
import typing as t

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

    @property
    def typ(self) -> str:
        if self.b.is_jflow:
            return 'j'
        if self.b.is_stgit:
            return 's'
        return '.'

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

    @property
    def review(self) -> str:
        if self.b.review_resolved and self.b.ref != self.b.review_resolved:
            return 'R'
        if self.b.public_resolved and self.b.ref != self.b.public_resolved:
            return 'r'
        return '.'

    @property
    def debug(self) -> str:
        if self.b.debug_resolved and self.b.ref != self.b.debug_resolved:
            return 'D'
        if self.b.ldebug_resolved and self.b.ref != self.b.ldebug_resolved:
            return 'd'
        return '.'

    @property
    def merged(self) -> str:
        r = '.'
        if self.b.upstream_resolved and self.is_merged_into(self.b.upstream_resolved):
            r = 'U'
        if self.b.fork_resolved and self.is_merged_into(self.b.fork_resolved):
            r = 'F'
        develop_ref = self.gc.refs.get(self.DEVELOP_REF, None)
        if self.b.ref != develop_ref and self.is_merged_into(develop_ref):
            r = 'D'
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


@root.group.command('list')
def list_cmd():
    '''List branches.'''

    gc = repo.Cache()

    print('''
+------- 'j' = controlled by jflow; 's' = controlled by StGit
|+------ 'r' = has local review branch; 'R' = has remote review
||+----- 'd' = has local debug branch; 'D' = has remote debug
|||+---- merged into: 'U' = upstream; 'F' = fork; 'D' = develop; 'M' = master
||||''')
    branches = list(gc.branches.values())
    maxlen = max(len(b.name) for b in branches)
    for b in branches:
        if b.hidden:
            continue
        print('{i.typ}{i.review}{i.debug}{i.merged} {c.W}{b.name}{c.N}{i.name_pad}{i.description}'.format(
            i=ListLine(gc, b, maxlen=maxlen), b=b, c=color.Colors,
        ))
