#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to rebase a branch."""

from dsapy import app
from dsapy import flag


class Rebase(app.Command):
    '''Rebase a branch.'''
    name='rebase'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'base',
            metavar='BASE',
            nargs='?',
            help=(
                'Name of the new upstream.'
                '  By default, use the current upstream.'
            ),
        )

    def main(self):
        print('Command: "rebase"')
        print(self.flags)


if __name__ == '__main__':
    app.start()
