#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

from typing import *

import collections
import logging

from dsapy import app
from dsapy import flag

from jf import command
from jf import common
from jf import config
from jf import git
from jf import sync


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


@app.main()
def templates(**kwargs):
    gc = git.Cache()
    templates = gc.cfg.jf.templates_list
    print(f'Templates: {templates!r}')


class Start(app.Command):
    '''Start a new branch.'''

    name='start'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--upstream',
            metavar='BRANCH',
            help='Use this branch as `upstream` parameter',
        )
        parser.add_argument(
            '--fork',
            metavar='BRANCH',
            help='Use this branch as `fork` parameter',
        )
        parser.add_argument(
            '--lreview',
            metavar='BRANCH',
            help='Use this name for local review branch',
        )
        parser.add_argument(
            '--review',
            metavar='BRANCH',
            help='Use this name for remote review branch',
        )
        parser.add_argument(
            '--ldebug',
            metavar='BRANCH',
            help='Use this name for local debug branch',
        )
        parser.add_argument(
            '--debug',
            metavar='BRANCH',
            help='Use this name for remote debug branch',
        )

        parser.add_argument(
            'name',
            metavar='BRANCH',
            help='Name of the branch to start',
        )

    _defaults = [
        ('fork', 'upstream'),
        ('ldebug_suffix', 'debug_suffix'),
    ]

    def main(self) -> None:
        git.check_workdir_is_clean()

        gc = git.Cache()

        name = self.flags.name
        matches = []
        for t in gc.cfg.jf.templates_list:
            if (
                name.startswith(t)
                and gc.cfg.jf.template(t).version.as_int == 1
            ):
                matches.append(t)
        if not matches:
            raise Error('Prefix not found')
        matches.sort(key=len)

        return self.main_v1(gc, name, matches)

    def main_v1(self, gc: git.Cache, name: str, matches: List[str]) -> None:
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
            tk = gc.cfg.jf.template(t)
            for k in config.JfTemplateKey.KEYS:
                kk = getattr(tk, k)
                if kk.value is None:
                    continue
                tc[k] = kk.value

        for t, s in self._defaults:
            if t not in tc and s in tc:
                tc[t] = tc[s]

        rc: Dict[str, Optional[str]] = {
            'version': tc.get('version', None),
            'public': self.flags.lreview or f'{tc["lreview_prefix"]}{base}{tc["lreview_suffix"]}',
            'review': self.flags.review or f'{tc["review_prefix"]}{base}{tc["review_suffix"]}',
            'ldebug': self.flags.ldebug or f'{tc["ldebug_prefix"]}{base}{tc["ldebug_suffix"]}',
            'debug': self.flags.debug or f'{tc["debug_prefix"]}{base}{tc["debug_suffix"]}',
            'debug_prefix': tc['debug_prefix'],
            'debug_suffix': tc['debug_suffix'],
        }

        upstream_shortcut = self.flags.upstream or tc['upstream']
        upstream_ref = gc.resolve_shortcut(upstream_shortcut)
        if not upstream_ref:
            raise Error(f'Cannot detect upstream for {upstream_shortcut!r}')
        if not upstream_ref.branch_name:
            raise Error('Unsupported ref kind: {upstream_ref.name!r}')
        rc['upstream'] = upstream_ref.branch_name

        fork_shortcut = self.flags.fork or tc['fork']
        fork_ref: Optional[git.RefName] = gc.resolve_shortcut(fork_shortcut)
        if not fork_ref:
            raise Error(f'Cannot detect fork for {fork_shortcut!r}')
        if not fork_ref.branch_name:
            raise Error('Unsupported ref kind: {fork_ref.name!r}')
        rc['fork'] = fork_ref.branch_name

        if fork_ref.is_remote:
            command.run(['git', 'branch', '--force', fork_ref.branch_name, fork_ref.name])
            bk = gc.cfg.branch(fork_ref.branch_name).jf
            bk.sync.set('true')
            fork_ref = git.RefName.for_branch(git._REMOTE_LOCAL, fork_ref.branch_name)

        command.run(['stg', 'branch', '--create', name, fork_ref.name])
        command.run(['stg', 'new', '--message=WIP', 'wip'])

        bk = gc.cfg.branch(name).jf
        for kk, kv in rc.items():
            if not kv:
                continue
            getattr(bk, kk).set(kv)


if __name__ == '__main__':
    app.start()
