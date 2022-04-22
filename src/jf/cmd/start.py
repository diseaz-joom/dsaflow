#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

import collections
import logging
import typing as t

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
@click.option('--review',
              help='Use this name for remote review branch')
@click.option('--review-local',
              help='Use this name for local review branch')
@click.option('--debug',
              help='Use this name for remote debug branch')
@click.option('--debug-local',
              help='Use this name for local debug branch')
def start(
        name: str,
        description: t.Optional[str],
        upstream: t.Optional[str],
        fork: t.Optional[str],
        review: t.Optional[str],
        review_local: t.Optional[str],
        debug: t.Optional[str],
        debug_local: t.Optional[str],
):
    '''Starts new branch NAME.'''

    git.check_workdir_is_clean()

    gc = repo.Cache()

    # Find all prefixes that match new branch
    matches = []
    for k in gc.cfg.jf.template.keys:
        if (
            name.startswith(k)
            and gc.cfg.jf.template[k].version.value
        ):
            matches.append(k)
    if not matches:
        raise Error('Prefix not found')
    matches.sort(key=len)

    prefix = matches[-1]  # Longest prefix
    base = name[len(prefix):]  # Base name with prefix stripped

    # Build config from templates matched
    template_cfg: t.Dict[str, str] = collections.defaultdict(
        lambda: '',
        lreview_prefix=prefix,
        review_prefix=prefix,
        ldebug_prefix=prefix,
        debug_prefix=prefix,
    )

    for m in matches:
        tk = gc.cfg.jf.template[m]
        for k in config.JfTemplateCfg.KEYS:
            kk = getattr(tk, k)
            if kk.value is None:
                continue
            template_cfg[k] = kk.value

    for d, s in _defaults:
        if d not in template_cfg and s in template_cfg:
            template_cfg[d] = template_cfg[s]

    # Build branch config
    branch_cfg: t.Dict[str, t.Optional[str]] = {
        'version': template_cfg.get('version', None),
        'lreview': review_local or f'{template_cfg["lreview_prefix"]}{base}{template_cfg["lreview_suffix"]}',
        'review': review or f'{template_cfg["review_prefix"]}{base}{template_cfg["review_suffix"]}',
        'ldebug': debug_local or f'{template_cfg["ldebug_prefix"]}{base}{template_cfg["ldebug_suffix"]}',
        'debug': debug or f'{template_cfg["debug_prefix"]}{base}{template_cfg["debug_suffix"]}',
        'debug_prefix': template_cfg['debug_prefix'],
        'debug_suffix': template_cfg['debug_suffix'],
    }

    upstream_shortcut = upstream or template_cfg['upstream']
    upstream_ref = gc.resolve_shortcut(upstream_shortcut)
    if not upstream_ref:
        raise Error(f'Cannot resolve {upstream_shortcut!r}')
    if not upstream_ref.branch:
        raise Error('Not a branch: {upstream_ref.name!r}')
    branch_cfg['upstream'] = upstream_ref.branch
    if upstream_ref != upstream_shortcut:
        branch_cfg['upstream_shortcut'] = upstream_shortcut

    fork_shortcut = fork or template_cfg['fork'] or gc.cfg.branch[upstream_ref.branch].jf.fork_from.value
    fork_ref: t.Optional[git.RefName] = gc.resolve_shortcut(fork_shortcut)
    if not fork_ref:
        raise Error(f'Cannot detect fork for {fork_shortcut!r}')
    if not fork_ref.branch:
        raise Error('Unsupported ref kind: {fork_ref.name!r}')
    branch_cfg['fork'] = fork_ref.branch
    if fork_ref != fork_shortcut:
        branch_cfg['fork_shortcut'] = fork_shortcut

    if fork_ref.is_remote:
        if not fork_ref.branch:
            raise Error(f'Strange remote non-branch: {fork_ref!r}')
        command.run(['git', 'branch', '--force', fork_ref.branch, fork_ref])
        bk = gc.cfg.branch[fork_ref.branch].jf
        bk.sync.set(True)
        fork_ref = fork_ref.branch.ref(git.REMOTE_LOCAL)

    command.run(['stg', 'branch', '--create', name, fork_ref])
    command.run(['stg', 'new', '--message=WIP', 'wip'])

    bk = gc.cfg.branch[name].jf
    for kk, kv in branch_cfg.items():
        if not kv:
            continue
        getattr(bk, kk).set(kv)

    if description:
        gc.cfg.branch[name].description.set(description)


_defaults = [
    ('fork', 'upstream'),
    ('ldebug_suffix', 'debug_suffix'),
]
