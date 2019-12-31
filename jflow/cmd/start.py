#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Command to start a new branch."""

from dsapy import app
from dsapy import flag


class Start(app.Command):
    '''Start a new branch.'''
    name='start'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'name',
            metavar='NAME',
            help='Name of the branch to start',
        )

    def main(self):
        print('Command: "start"')
        print(self.flags)


if __name__ == '__main__':
    app.start()
