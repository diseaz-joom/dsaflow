#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Print current ref."""


from dsapy import app

from jflow import git


class Error(Exception):
    '''Base class for errors in the module.'''


class CurrentRef(git.Git, app.Command):
    '''Publish a branch.'''
    name='current-ref'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--short',
            action='store_true',
            help='Print abbreviated reference representation',
        )

    def main(self):
        print(self.git_current_ref(short=self.flags.short))


if __name__ == '__main__':
    app.start()
