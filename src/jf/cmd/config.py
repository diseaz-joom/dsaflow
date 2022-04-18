#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import click

from jf import config
from jf import git
from jf import repo
from jf.cmd import root


class Error(Exception):
    '''Base for errors in the module.'''


@root.group.command('config')
@click.option('-b', '--branch', default=git.current_branch, help='Branch to operate on')
@click.option('-s', '--set', 'set_', help='Name of the config key to set.')
@click.option('-v', '--value', help='Value to set. Unset if missing.')
def config_cmd(branch: str, set_: str, value: str):
    '''Display or modify branch config.'''

    gc = repo.Cache()
    b = gc.branches[branch]
    if set_:
        k = getattr(gc.cfg.branch[b.name].jf, set_)
        if value is None:
            k.unset()
        else:
            k.set_str(value)
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
