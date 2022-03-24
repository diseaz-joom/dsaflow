#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Open jenkins build page."""

import urllib.parse as up

from dsapy import app
from dsapy import flag

from jf import command
from jf import config
from jf import git
from jf import jenkins


class Jenkins(app.Command):
    '''Open jenkins build page.'''
    name='jenkins'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--debug',
            action='store_true',
            help='Alternative public branch for debugging without spamming PR',
        )
        parser.add_argument(
            'branch',
            nargs='?',
            default=git.current_branch,
            help='Branch to operate on',
        )

    def main(self):
        gc = git.Cache()

        branch_name = self.flags.branch
        if not branch_name:
            raise Error('HEAD is not a branch')
        branch = gc.branches[branch_name]

        build_branch_name = branch.debug_branch_name if self.flags.debug else branch.review_branch_name
        url = jenkins.branch_url(build_branch_name)
        command.run(['xdg-open', url])
