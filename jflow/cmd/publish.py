#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Publish a branch."""

import logging
import re

from dsapy import app

import jflow
from jflow import config
from jflow import git
from jflow import publish
from jflow import run
from jflow import struct


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Publish(publish.ParamsMixin, git.Git, app.Command):
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

    REMOTE_RE = re.compile('(?:https://)?github\\.com[:/](?P<repo>.*?)(?:\.git)?$')

    def main(self):
        p = self.params(
            local=self.flags.local,
            pr=self.flags.pr,
        )

        self.publish_local(p.current_branch, p.public_branch_name, force_new=self.flags.new)

        if self.flags.local:
            return

        self.cmd_action([
            'git', 'push', '--force', p.remote_name,
            '{public}:{remote}'.format(
                public=p.public_branch_name,
                remote=p.remote_branch_name,
            )])

        if not self.flags.pr or p.debug:
            return

        self.cmd_action(['xdg-open', p.pr_url])


if __name__ == '__main__':
    app.start()
