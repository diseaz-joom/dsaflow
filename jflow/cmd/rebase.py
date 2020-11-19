#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to rebase a branch."""

import logging
import pprint

from dsapy import app
from dsapy import flag

from jflow import branch
from jflow import config
from jflow import publish
from jflow import sync


_logger = logging.getLogger(__name__)


class Rebase(sync.SyncMixin, publish.ToolsMixin, branch.Controller, app.Command):
    '''Rebase a branch.'''
    name='rebase'

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
            '--sync',
            action='store_true',
            help='Sync before rebase',
        )

    def main(self):
        self.git_check_workdir_is_clean()
        if self.flags.sync:
            self.sync()

        branch = self.git_current_ref(short=True)
        branch_conf = {
            v.key():v.value
            for v in self.git_config_get_regex(
                    config.make_prefix(config.branch_key_base(branch)),
                    None,
            )
        }

        public_branch = self.public_branch(branch)
        need_publish = public_branch and self.git_branch_exists(public_branch)
        if need_publish:
            self.publish_local(branch, public_branch)

        heads = list(self.branch_iter_tree())

        upstream_name = branch_conf.get(config.KEY_UPSTREAM)
        fork_name = branch_conf.get(config.KEY_FORK)

        upstream_b = self.branch_resolve(upstream_name, heads=heads)
        fork_b = self.branch_resolve(fork_name, heads=heads)

        new_upstream_b = upstream_b
        new_fork_b = fork_b
        if self.flags.upstream is not None:
            new_upstream_b = self.branch_resolve(self.flags.upstream, heads=heads)
            if self.flags.fork is None and upstream_b == fork_b:
                new_fork_b = new_upstream_b
        if self.flags.fork is not None:
            new_fork_b = self.branch_resolve(self.flags.fork, heads=heads)

        self.cmd_action(['stg', 'rebase', '--merged', new_fork_b.full_ref()])
        self.cmd_action(['git', 'clean', '-d', '--force'])
        self.cmd_action_pipe([
            ['git', 'ls-files', '--others', '--directory', '--exclude-standard'],
            ['xargs', 'rm', '--recursive', '--force', '--verbose'],
        ])

        if new_fork_b != fork_b:
            self.git_config_set(config.branch_key_fork(branch), new_fork_b.branch)
        if new_upstream_b != upstream_b:
            self.git_config_set(config.branch_key_upstream(branch), new_upstream_b.branch)

        if need_publish:
            self.publish_local(branch, public_branch)


if __name__ == '__main__':
    app.start()
