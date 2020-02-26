#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Publish a branch."""

import logging
import re

from dsapy import app

import jflow
from jflow import config
from jflow import git
from jflow import run
from jflow import struct


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class PublishTools(git.Git, run.Cmd):
    def public_branch(self, branch=None):
        branch = branch or self.git_current_ref(short=True)
        return self.git_config_get(config.branch_key_public(branch))

    def publish_local(self, current_branch, public_branch, force_new=False):
        if current_branch == public_branch:
            return
        if force_new:
            self.cmd_action(['stg', 'branch', '--delete', '--force', public_branch])
        self.cmd_action(['stg', 'publish', public_branch])


class Publish(PublishTools, git.Git, app.Command):
    '''Publish a branch.'''
    name='publish'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--new',
            action='store_true',
            help='Start public branch anew',
        )
        parser.add_argument(
            '--local',
            action='store_true',
            help='Only update local public branch',
        )
        parser.add_argument(
            '--pr',
            action='store_true',
            help='Create PR',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Alternative public branch for debugging without spamming PR',
        )

    REMOTE_RE = re.compile('(?:https://)?github\\.com[:/](?P<repo>.*?)(?:\.git)?$')

    def main(self):
        current_branch = self.git_current_ref(short=True)
        public_branch_name = self.public_branch(current_branch)

        if self.flags.debug:
            public_branch_name = current_branch

        self.publish_local(current_branch, public_branch_name, force_new=self.flags.new)

        if self.flags.local:
            return

        # TODO(diseaz): take remote of the upstream branch upstream.
        remote_name = 'origin'
        remote_branch_name = current_branch

        if self.flags.debug:
            remote_branch_name = current_branch + '.debug'

        self.cmd_action([
            'git', 'push', '--force', 'origin',
            '{public}:{remote}'.format(
                public=public_branch_name,
                remote=remote_branch_name,
            )])

        if not self.flags.pr or self.flags.debug:
            return

        upstream_branch_name = self.git_config_get(config.branch_key_upstream(current_branch))
        remote_url = self.git_config_get(config.remote_key_url(remote_name))
        if not remote_url:
            _logger.info('No URL found for %r', remote_name)
            return
        url_m = self.REMOTE_RE.match(remote_url)
        if url_m is None:
            _logger.info('Remote URL %r does not match any known pattern', remote_url)
            return
        pr_url = 'https://github.com/{repo}/compare/{upstream}...{remote}?expand=1'.format(
            repo=url_m.group('repo'),
            upstream=upstream_branch_name,
            remote=remote_branch_name,
        )
        self.cmd_action(['xdg-open', pr_url])


if __name__ == '__main__':
    app.start()
