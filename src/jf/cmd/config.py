#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from dsapy import app

from jf import config
from jf import git


class Error(Exception):
    '''Base for errors in the module.'''


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
            k = getattr(gc.cfg.branch[b.name].jf, self.flags.set)
            if self.flags.value is None:
                k.unset()
            else:
                k.set_str(self.flags.value)
        else:
            bk = gc.cfg.branch[b.name]
            for k in ['remote', 'merge']:
                kk = getattr(bk, k)
                if kk.value is None:
                    continue
                print(f'{kk.path} {kk.value}')
            sk = bk.stgit
            for k in ['version', 'parentbranch']:
                kk = getattr(sk, k)
                if kk.value is None:
                    continue
                print(f'{kk.path} {kk.value}')
            jp = gc.cfg.branch[b.name].jf.path + config.SEPARATOR
            for k, v in gc.cfg.raw.items():
                if not k.startswith(jp):
                    continue
                print(f'{k} {v!r}')


class Info(app.Command):
    name = 'info'

    _BRANCH_PROPS = [
        'name',
        'remote',
        'is_jflow',
        'is_stgit',
        'upstream_name',
        'upstream',
        'fork_name',
        'fork',
        'ldebug_name',
        'ldebug',
        'debug_name',
        'debug',
        'public_name',
        'public',
        'review_name',
        'review',
        'hidden',
        'protected',
        'sync',
        'tested',
    ]

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
        for k in self._BRANCH_PROPS:
            kv = getattr(b, k)
            print(f'  {k}: {kv!r}')
        bk = gc.cfg.branch[b.name].jf
        print(f'Jflow config ({bk.path}):')
        for k in config.JfBranchCfg.KEYS:
            kk = getattr(bk, k)
            print(f'  {k}: {kk.value!r}')
