#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Open branch in GitHub."""

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


class GitHubCmd(publish.ParamsMixin, git.Git, app.Command):
    '''Open branch in GitHub.'''
    name='gh'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--print',
            action='store_true',
            help='Only print URL, do not open a browser',
        )

    REMOTE_RE = re.compile('(?:https://)?github\\.com[:/](?P<repo>.*?)(?:\.git)?$')

    def main(self):
        p = self.params(
            need_url=True,
            expand=False,
        )
        if self.flags.print:
            print(p.pr_url)
        else:
            self.cmd_action(['xdg-open', p.pr_url])


if __name__ == '__main__':
    app.start()
