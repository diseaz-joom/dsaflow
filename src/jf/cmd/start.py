#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

from typing import Dict, Optional

import collections
import logging

import click

from jf import command
from jf import config
from jf import git
from jf import repo
from jf.cmd import root


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


@root.group.command()
@click.argument('name')
@click.option('-d', '--description',
              help='Description for a new branch')
@click.option('--upstream',
              help='Use this branch as `upstream` parameter')
@click.option('--fork',
              help='Use this branch as `fork` parameter')
@click.option('--lreview',
              help='Use this name for local review branch')
@click.option('--review',
              help='Use this name for remote review branch')
@click.option('--ldebug',
              help='Use this name for local debug branch')
@click.option('--debug',
              help='Use this name for remote debug branch')
def start(
        name: str,
        description: Optional[str],
        upstream: Optional[str],
        fork: Optional[str],
        lreview: Optional[str],
        review: Optional[str],
        ldebug: Optional[str],
        debug: Optional[str],
):
    '''Starts new branch NAME.'''

    git.check_workdir_is_clean()

    gc = repo.Cache()

    matches = []
    for t in gc.cfg.jf.template.keys:
        if (
            name.startswith(t)
            and gc.cfg.jf.template[t].version.value == 1
        ):
            matches.append(t)
    if not matches:
        raise Error('Prefix not found')
    matches.sort(key=len)

    prefix = matches[-1]
    base = name[len(prefix):]

    tc: Dict[str, str] = collections.defaultdict(
        lambda: '',
        lreview_prefix=prefix,
        review_prefix=prefix,
        ldebug_prefix=prefix,
        debug_prefix=prefix,
    )

    for t in matches:
        tk = gc.cfg.jf.template[t]
        for k in config.JfTemplateCfg.KEYS:
            kk = getattr(tk, k)
            if kk.value is None:
                continue
            tc[k] = kk.value

    for t, s in _defaults:
        if t not in tc and s in tc:
            tc[t] = tc[s]

    rc: Dict[str, Optional[str]] = {
        'version': tc.get('version', None),
        'lreview': lreview or f'{tc["lreview_prefix"]}{base}{tc["lreview_suffix"]}',
        'review': review or f'{tc["review_prefix"]}{base}{tc["review_suffix"]}',
        'ldebug': ldebug or f'{tc["ldebug_prefix"]}{base}{tc["ldebug_suffix"]}',
        'debug': debug or f'{tc["debug_prefix"]}{base}{tc["debug_suffix"]}',
        'debug_prefix': tc['debug_prefix'],
        'debug_suffix': tc['debug_suffix'],
    }

    upstream_shortcut = upstream or tc['upstream']
    upstream_ref = gc.resolve_shortcut(upstream_shortcut)
    if not upstream_ref:
        raise Error(f'Cannot detect upstream for {upstream_shortcut!r}')
    if not upstream_ref.branch_name:
        raise Error('Unsupported ref kind: {upstream_ref.name!r}')
    rc['upstream'] = upstream_ref.branch_name

    fork_shortcut = fork or tc['fork']
    fork_ref: Optional[git.RefName] = gc.resolve_shortcut(fork_shortcut)
    if not fork_ref:
        raise Error(f'Cannot detect fork for {fork_shortcut!r}')
    if not fork_ref.branch_name:
        raise Error('Unsupported ref kind: {fork_ref.name!r}')
    rc['fork'] = fork_ref.branch_name

    if fork_ref.is_remote:
        command.run(['git', 'branch', '--force', fork_ref.branch_name, fork_ref.name])
        bk = gc.cfg.branch[fork_ref.branch_name].jf
        bk.sync.set(True)
        fork_ref = git.RefName.for_branch(git.REMOTE_LOCAL, fork_ref.branch_name)

    command.run(['stg', 'branch', '--create', name, fork_ref.name])
    command.run(['stg', 'new', '--message=WIP', 'wip'])

    bk = gc.cfg.branch[name].jf
    for kk, kv in rc.items():
        if not kv:
            continue
        getattr(bk, kk).set(kv)

    if description:
        gc.cfg.branch[name].description.set(description)


_defaults = [
    ('fork', 'upstream'),
    ('ldebug_suffix', 'debug_suffix'),
]
