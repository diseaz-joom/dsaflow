#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to rebase a branch."""

from dsapy import app
from dsapy import flag

from jflow import branch
from jflow import config
from jflow import publish
from jflow import sync


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

        branch_upstream = branch_conf.get(config.KEY_UPSTREAM)
        branch_fork = branch_conf.get(config.KEY_FORK)

        new_upstream = branch_upstream
        new_fork = branch_fork
        if self.flags.upstream is not None:
            new_upstream = self.branch_resolve(self.flags.upstream, heads=heads).branch
            if self.flags.fork is None and branch_upstream == branch_fork:
                new_fork = new_upstream
        if self.flags.fork is not None:
            new_fork = self.branch_resolve(self.flags.fork, heads=heads).branch

        self.cmd_action(['stg', 'rebase', '--merged', new_fork])
        self.cmd_action(['git', 'clean', '-d', '--force'])

        if new_fork != branch_fork:
            self.git_config_set(config.branch_key_fork(branch), new_fork)
        if new_upstream != branch_upstream:
            self.git_config_set(config.branch_key_upstream(branch), new_upstream)

        if need_publish:
            self.publish_local(branch, public_branch)


if __name__ == '__main__':
    app.start()
