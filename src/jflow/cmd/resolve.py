#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Resolve a branch family name into a latest branch name."""

import logging

from dsapy import app

from jflow import branch


_logger = logging.getLogger(__name__)


class Resolve(branch.Controller, app.Command):
    '''Resolve a branch family name into a latest branch name.'''
    name='resolve'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--ref',
            action='store_true',
            help='Print full ref name',
        )
        parser.add_argument(
            'name',
            metavar='NAME',
            help='Name to resolve',
        )

    def main(self):
        resolved = self.branch_resolve(self.flags.name)
        if resolved:
            if self.flags.ref:
                print(resolved.full_ref())
            else:
                print(resolved.branch)


if __name__ == '__main__':
    app.start()
