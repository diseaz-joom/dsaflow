#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from dsapy import app

from jf import config
from jf import git


class Error(Exception):
    '''Base for errors in the module.'''


@app.main(name='current-ref')
def current_ref(**kwargs):
    '''Print current ref name.'''
    if not git.current_ref:
        return
    print(git.current_ref)


class Resolve(app.Command):
    name = 'resolve'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'shortcut',
            help='Shortcut to resolve',
        )

    def main(self):
        gc = git.Cache()
        r = gc.resolve_shortcut(self.flags.shortcut)
        print(f'Resolved: {r!r}')


class Templates(app.Command):
    name = 'templates'

    def main(self):
        cfg = config.Root()
        for t in cfg.jf.template.keys:
            print(f'{t!r}')


class Config(app.Command):
    name = 'configv2'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-b', '--branch',
            default=git.current_branch,
            help='Branch to operate on',
        )

    def main(self):
        cfg = config.Root()

        gc = git.Cache()
        b = gc.branches[self.flags.branch]

        bk = cfg.branch[b.name]
        for k in ['remote', 'merge']:
            kk = getattr(bk, k)
            print(f'{kk.path} {kk.value!r}')

        sk = bk.stgit
        for k in ['version', 'parentbranch']:
            kk = getattr(sk, k)
            print(f'{kk.path} {kk.value!r}')

        jk = bk.jf
        for k in config.JfBranchCfg.KEYS:
            kk = getattr(jk, k)
            print(f'{kk.path} {kk.value!r}')
