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


_jflow_keys = ['version', 'public', 'debug', 'ldebug', 'upstream', 'fork', 'review', 'hidden', 'tested', 'sync']


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
            k = getattr(gc.cfg.branch(b.name).jf, self.flags.set)
            if self.flags.value is None:
                k.unset()
            else:
                k.set(self.flags.value)
        else:
            bk = gc.cfg.branch(b.name)
            for k in ['remote', 'merge']:
                kk = getattr(bk, k)
                if kk.value is None:
                    continue
                print(f'{kk.key} {kk.value}')
            bk = gc.cfg.branch(b.name).stgit
            for k in ['version', 'parentbranch']:
                kk = getattr(bk, k)
                if kk.value is None:
                    continue
                print(f'{kk.key} {kk.value}')
            bk = gc.cfg.branch(b.name).jf
            for k in _jflow_keys:
                kk = getattr(bk, k)
                if kk.value is None:
                    continue
                print(f'{kk.key} {kk.value}')


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
        for k in ['name', 'is_jflow', 'is_stgit', 'upstream_name', 'upstream', 'fork_name', 'fork', 'public_name', 'public', 'debug_name', 'debug', 'ldebug_name', 'ldebug', 'review_name', 'review', 'hidden', 'tested']:
            kv = getattr(b, k)
            print(f'  {k}: {kv!r}')
        bk = gc.cfg.branch(b.name).jf
        print(f'Jflow config ({bk.key}):')
        for k in _jflow_keys:
            kv = getattr(bk, k).value
            print(f'  {k}: {kv!r}')


@app.main(name='current-ref')
def current_ref(**kwargs):
    '''Print current ref name.'''
    if not git.current_ref:
        return
    print(git.current_ref)
