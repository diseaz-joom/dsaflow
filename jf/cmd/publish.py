#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Rebase branch to a fresh tip."""

from typing import *

import logging
import re

from dsapy import app

from jf import command
from jf import config
from jf import git
from jf import green
from jf import sync


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Review:
    GITHUB_REMOTE_RE = re.compile('(?:https://|[-_+a-z0-9]+@)?github\\.com[:/](?P<repo>.*?)(?:\.git)?$')

    def github_review_url(self, remote_url: str, feature: git.RefName, upstream: git.RefName) -> Optional[str]:
        github_m = self.GITHUB_REMOTE_RE.match(remote_url)
        if not github_m:
            return None

        repo_name = github_m['repo']

        return f'https://github.com/{repo_name}/compare/{upstream.branch_name}...{feature.branch_name}'


    def review_url(self, gc: git.Cache, feature: git.RefName, upstream: git.RefName) -> Optional[str]:
        if not feature.remote:
            return None

        remote_url = gc.cfg.remote(feature.remote).url.value
        if not remote_url:
            return None

        return self.github_review_url(remote_url, feature, upstream)


class Publish(Review, app.Command):
    '''Publish a branch.'''

    name='publish'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-m', '--message',
            metavar='MESSAGE',
            default=None,
            help='Message to commit current changes before rebase',
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Alternative public branch for debugging without spamming PR',
        )
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
            '--non-clean',
            action='store_true',
            help='Force action with non clean workdir',
        )

    def main(self):
        if not self.flags.non_clean:
            git.check_workdir_is_clean()

        gc = git.Cache()

        branch_name = git.current_branch
        if not branch_name:
            raise Error('HEAD is not a branch')
        branch = gc.branches[branch_name]

        if self.flags.debug:
            publish_func = branch.publish_local_debug
        else:
            publish_func = branch.publish_local_public

        local_ref, remote_ref = publish_func(msg=self.flags.message, force_new=self.flags.new)

        if self.flags.local:
            return

        if not remote_ref:
            raise Error('No remote reference calculated')
        if not remote_ref.branch_name:
            raise Error(f'Failed to extract branch name from ref {remote_ref_name.name}')
        remote_branch_ref = git.RefName.for_branch(git._REMOTE_LOCAL, remote_ref.branch_name)

        command.run([
            'git', 'push', '--force', remote_ref.remote,
            '{public}:{remote}'.format(
                public=local_ref.name,
                remote=remote_branch_ref.name,
            )])

        if not self.flags.pr:
            return

        pr_url = self.review_url(gc, remote_ref, branch.upstream_name)
        command.run(['xdg-open', pr_url])
