#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import functools
import sys

from dsapy import app
from dsapy.algs import strconv

from jf import color
from jf import git


class Error(Exception):
    '''Base for errors in the module.'''


_jflow_keys = ['version', 'public', 'debug', 'upstream', 'fork', 'remote', 'hidden', 'tested', 'sync']


class Config(app.Command):
    name = 'config'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-b', '--branch',
            default=git.current_branch,
            help='Branch to operate on',
        )

        parser.add_argument(
            '-s', '--set',
            default=None,
            help='Name of the config key to set.',
        )
        parser.add_argument(
            '-v', '--value',
            default=None,
            help='Value to set. Unset if missing.',
        )

    def main(self):
        gc = git.Cache()
        b = gc.branches[self.flags.branch]
        if self.flags.set:
            k = getattr(gc.cfg.branch(b.name).jf(), self.flags.set)()
            if self.flags.value is None:
                k.unset()
            else:
                k.set(self.flags.value)
        else:
            bk = gc.cfg.branch(b.name)
            for k in ['remote', 'merge']:
                kk = getattr(bk, k)()
                kv = kk.get()
                if kv is None:
                    continue
                print(f'{kk.key()} {kv}')
            bk = gc.cfg.branch(b.name).stgit()
            for k in ['version', 'parentbranch']:
                kk = getattr(bk, k)()
                kv = kk.get()
                if kv is None:
                    continue
                print(f'{kk.key()} {kv}')
            bk = gc.cfg.branch(b.name).jf()
            for k in _jflow_keys:
                kk = getattr(bk, k)()
                kv = kk.get()
                if kv is None:
                    continue
                print(f'{kk.key()} {kv}')


class Info(app.Command):
    name = 'info'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'branch',
            nargs='?',
            default=git.current_branch,
            help='Branch to operate on',
        )

    def main(self):
        gc = git.Cache()
        b = gc.branches[self.flags.branch]
        print('Branch:')
        for k in ['name', 'is_jflow', 'is_stgit', 'public', 'debug', 'remote', 'fork_ref_name', 'fork', 'upstream_ref_name', 'upstream', 'hidden', 'tested_branch_name']:
            kv = getattr(b, k)
            print(f'  {k}: {kv!r}')
        print('Config:')
        bk = gc.cfg.branch(b.name).jf()
        for k in _jflow_keys:
            kv = getattr(bk, k)().get()
            print(f'  {k}: {kv!r}')


class Hide(app.Command):
    name='hide'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--set',
            action='store',
            type=strconv.parse_bool,
            dest='hide',
            default=True,
            help='Hide branch',
        )

        parser.add_argument(
            'branch',
            nargs='?',
            default=git.current_branch,
            help='Branch to operate on',
        )

    def main(self):
        if not self.flags.branch:
            raise Error('Branch is required')

        gc = git.Cache()

        branch = gc.branch_by_abbrev.get(self.flags.branch, None)
        if not branch:
            raise Error(f'Branch not found: {self.flags.branch}')

        branch.set_hidden(self.flags.hide)


@app.main(name='current-ref')
def current_ref(**kwargs):
    '''Print current ref name.'''
    if not git.current_ref:
        return
    print(git.current_ref)
