#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Synchronization from upstream repo."""

from dsapy import app
from dsapy import flag

from jflow import git
from jflow import sync


class Error(Exception):
    '''Base for errors in the module.'''


class Sync(sync.SyncMixin, git.Git, app.Command):
    '''Synchronize from upstream repo.'''
    name='sync'

    def main(self):
        self.git_check_workdir_is_clean()
        self.sync()


if __name__ == '__main__':
    app.start()
