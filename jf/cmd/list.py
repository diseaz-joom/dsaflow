#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import functools

from dsapy import app
from dsapy.algs import strconv

from jf import color
from jf import config
from jf import git


class Error(Exception):
    '''Base for errors in the module.'''


class ListLine:
    def __init__(self, gc, b):
        self.gc = gc
        self.b = b

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
    def is_merged_into(self, m: git.Ref) -> bool:
        return m.is_valid and self.gc.is_merged_into(self.b.ref.sha, m.sha) # self.b.ref.is_merged_into(self.gc, m)

    @property
    def public(self) -> str:
        if self.b.public:
            return 'p'
        return '.'

    @property
    def remote(self) -> str:
        if self.b.remote:
            return 'r'
        return '.'

    @property
    def debug(self) -> str:
        if self.b.debug:
            return 'd'
        return '.'

    @property
    def merged(self) -> str:
        if not (self.b.upstream and self.is_merged_into(self.b.upstream)):
            return '.'
        if not (self.b.fork and self.is_merged_into(self.b.fork)):
            return 'U'
        if not self.is_merged_into(self.gc.refs['develop']):
            return 'F'
        if not self.is_merged_into(self.gc.refs['master']):
            return 'D'
        return 'M'

    @property
    def merged_master(self) -> str:
        return 'M' if self.is_merged_into(self.gc.refs['master']) else '.'

    @property
    def merged_develop(self) -> str:
        return 'D' if self.is_merged_into(self.gc.refs['develop']) else '.'

    @property
    def upstream(self) -> str:
        return git.Ref(self.b.upstream_ref_name, None).short


@app.main()
def list(flags, **kwargs):
    '''List branches.'''
    gc = git.Cache()

    print('''
+------- 'j' = controlled by jflow; 's' = controlled by StGit
|+------ 'p' = has public branch
||+----- 'r' = has remote branch for review and merging
|||+---- 'd' = has remote branch for debug
||||+--- merged into: 'U' = upstream; 'F' = fork; 'D' = develop; 'M' = master
|||||''')
    for b in gc.branches.values():
        if b.hidden:
            continue
        print('{i.typ}{i.public}{i.remote}{i.debug}{i.merged} {c.W}{b.name}{c.N}'.format(
            i=ListLine(gc, b), b=b, c=color.Colors,
        ))


def _run():
    app.start()


if __name__ == '__main__':
    _run()
