#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Open jenkins build page."""

import urllib.parse as up

from dsapy import app
from dsapy import flag

from jflow import git
from jflow import run


class Jenkins(git.Git, run.Cmd, app.Command):
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

    def main(self):
        ref = self.git_current_ref(short=True)
        if self.flags.debug:
            ref = ref + '.debug'
        ref_escaped = up.quote(up.quote(ref, safe=''), safe='')
        url = 'https://jenkins.joom.it/job/backend-api/job/{}'.format(ref_escaped)
        self.cmd_action(['xdg-open', url])


if __name__ == '__main__':
    app.start()
