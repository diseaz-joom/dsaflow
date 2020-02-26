#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

import collections
import logging

from dsapy import app
from dsapy import flag

from jflow import branch
from jflow import config
from jflow import git
from jflow import run
from jflow import sync


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Start(sync.SyncMixin, branch.Controller, git.Git, run.Cmd, app.Command):
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
            '--public',
            metavar='BRANCH',
            help='Use this name for public branch',
        )
        parser.add_argument(
            '--debug',
            metavar='BRANCH',
            help='Use this name for debug branch',
        )
        parser.add_argument(
            '--remote',
            metavar='BRANCH',
            help='Use this name for remote branch',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Sync before rebase',
        )

        parser.add_argument(
            'name',
            metavar='NAME',
            help='Name of the branch to start',
        )

    def main(self):
        self.git_check_workdir_is_clean()
        if self.flags.sync:
            self.sync()

        name = self.flags.name
        matches = []  # A list of matched template names
        for v in self.git_config_get_regex(
                config.make_prefix(config.TEMPLATE_KEY_PREFIX),
                config.make_suffix(config.KEY_VERSION),
        ):
            key = v.key()
            if name.startswith(key):
                matches.append(key)
        if not matches:
            raise Error('Prefix not found')
        matches.sort(key=len)

        prefix = matches[-1]
        base = name[len(prefix):]

        tv = {
            v.key(): v.value
            for k in matches
            for v in self.git_config_get_regex(
                    config.make_prefix(config.TEMPLATE_KEY_PREFIX, k),
                    None,
            )
        }

        version = tv.get(config.KEY_VERSION, 1)

        public_prefix = tv.get(config.KEY_PUBLIC_PREFIX, prefix)
        public = self.flags.public or '{pp}{b}{ps}'.format(
            b=base,
            pp=public_prefix,
            ps=tv.get(config.KEY_PUBLIC_SUFFIX, ''),
        )

        debug = self.flags.debug or '{pp}{b}{ps}'.format(
            b=base,
            pp=tv.get(config.KEY_DEBUG_PREFIX, config.DEFAULT_DEBUG_PREFIX),
            ps=tv.get(config.KEY_DEBUG_SUFFIX, config.DEFAULT_DEBUG_SUFFIX),
        )

        remote = self.flags.remote or '{pp}{b}{ps}'.format(
            b=base,
            pp=tv.get(config.KEY_REMOTE_PREFIX, public_prefix),
            ps=tv.get(config.KEY_REMOTE_SUFFIX, ''),
        )

        heads = list(self.branch_iter_tree())
        upstream_b = self.branch_resolve(self.flags.upstream or tv.get(config.KEY_UPSTREAM), heads=heads)
        if not upstream_b:
            raise Error('No upstream branch found')

        fork_b = upstream_b
        fork_ref = self.flags.fork or tv.get(config.KEY_FORK)
        if fork_ref:
            fork_b = self.branch_resolve(fork_ref, heads=heads)
            if not fork_b:
                raise Error('Branch {!r} not found'.format(fork_ref))

        self.cmd_action(['stg', 'branch', '--create', name, fork_b.full_ref()])
        self.cmd_action(['stg', 'new', '--message=WIP', 'wip'])
        self.cmd_action(['git', 'branch', '--set-upstream-to={}'.format(upstream_b.full_ref())])

        self.git_config_set(config.branch_key_version(name), version)
        self.git_config_set(config.branch_key_public(name), public)
        self.git_config_set(config.branch_key_debug(name), debug)
        self.git_config_set(config.branch_key_remote(name), remote)
        self.git_config_set(config.branch_key_upstream(name), upstream_b.branch)
        self.git_config_set(config.branch_key_fork(name), fork_b.branch)


if __name__ == '__main__':
    app.start()
