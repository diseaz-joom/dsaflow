#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import click

from jf import config
from jf import git
from jf import repo
from jf.cmd import root


class Error(Exception):
    '''Base for errors in the module.'''


@root.group.group()
def debug():
    '''Commands for debugging the tool.'''
    return


@debug.command()
@click.option('-b', '--branch', default=git.current_branch, help='Branch to operate on')
def info(branch):
    '''Display branch info.'''
    gc = repo.Cache()
    b = gc.branches[branch]
    print('Branch:')
    for k in _BRANCH_PROPS:
        kv = getattr(b, k)
        print(f'  {k}: {kv!r}')
    bk = gc.cfg.branch[b.name].jf
    print(f'Jflow config ({bk.path}):')
    for k in config.JfBranchCfg.KEYS:
        kk = getattr(bk, k)
        print(f'  {k}: {kk.value!r}')


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
    'tested_branch_name',
    'tested',
]


@debug.command()
def commits():
    '''List commits.

    Commits are listed as repr of internal commit objects.
    '''
    gc = repo.Cache()
    for c in gc.commits.values():
        print(c)


@debug.command()
@click.argument('shortcut')
def resolve(shortcut):
    '''Resolve shortcut into ref.'''

    gc = repo.Cache()
    r = gc.resolve_shortcut(shortcut)
    print(f'Resolved: {r!r}')


@debug.command()
def templates():
    '''List templates.'''

    cfg = config.Root()
    for t in cfg.jf.template.keys:
        print(f'{t!r}')


@debug.command()
def refs(flags, **kwargs):
    '''List references.'''

    gc = git.Cache()
    for ref in gc.refs_list:
        print(f'{ref!r}')


@debug.command()
def refs_abbrevs():
    '''List reference abbreviations.'''

    gc = git.Cache()
    for abbrev, refs in gc.refs_abbrevs.items():
        print('{} -> {}'.format(
            abbrev,
            ', '.join(r.name for r in refs),
        ))


@debug.command()
@click.argument('ref', required=False, default=git.current_ref)
def abbrevs(ref):
    '''Display abbreviations for the REF.

    REF defaults to a current reference.
    '''

    for abbr in git.ref_abbrevs(ref):
        print(f'{abbr!r}')


if __name__ == '__main__':
    debug(auto_envvar_prefix='JF')
