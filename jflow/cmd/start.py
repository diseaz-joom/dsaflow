#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

import collections

from dsapy import app
from dsapy import flag

from jflow import branch
from jflow import config
from jflow import git
from jflow import run


class Error(Exception):
    '''Base class for errors in the module.'''


class Start(branch.Controller, git.Git, run.Cmd, app.Command):
    '''Start a new branch.'''
    name='start'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--branch.upstream',
            dest='branch_upstream',
            metavar='BRANCH',
            help='Use this branch as `upstream` parameter',
        )
        parser.add_argument(
            '--branch.from',
            dest='branch_from',
            metavar='BRANCH',
            help='Use this branch as `from` parameter',
        )
        parser.add_argument(
            '--branch.public',
            dest='branch_public',
            metavar='BRANCH',
            help='Use this name for public branch',
        )

        parser.add_argument(
            'name',
            metavar='NAME',
            help='Name of the branch to start',
        )

    def main(self):
        name = self.flags.name
        matches = []
        for v in self.git_config_get_regex('jflow.template.', '.version'):
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
            for v in self.git_config_get_regex('jflow.template.' + k + '.', None)
        }

        version = tv.get(config.KEY_VERSION, 1)

        public = self.flags.branch_public or '{pp}{b}{ps}'.format(
            b=base,
            pp=tv.get(config.KEY_PUBLIC_PREFIX, prefix),
            ps=tv.get(config.KEY_PUBLIC_SUFFIX, ''),
        )

        heads = list(self.branch_iter_tree())
        upstream_b = self.branch_resolve(self.flags.branch_upstream or tv.get(config.KEY_UPSTREAM), heads=heads)
        if not upstream_b:
            raise Error('No upstream branch found')

        from_b = upstream_b
        from_ref = self.flags.branch_from or tv.get(config.KEY_FROM)
        if from_ref:
            from_b = self.branch_resolve(from_ref, heads=heads)
            if not from_b:
                raise Error('Branch {!r} not found'.format(from_ref))

        self.git_config_set(config.branch_key_version(name), version)
        self.git_config_set(config.branch_key_public(name), public)
        self.git_config_set(config.branch_key_upstream(name), upstream_b.branch)
        self.git_config_set(config.branch_key_from(name), from_b.branch)

        self.cmd_action(['stg', 'branch', '--create', name, from_b.full_ref()])
        self.cmd_action(['stg', 'new', '--message=main', 'main'])
        self.cmd_action(['git', 'branch', '--set-upstream-to={}'.format(upstream_b.full_ref())])


if __name__ == '__main__':
    app.start()
