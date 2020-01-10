#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Resolve a branch family name into a latest branch name."""

import collections
import json
import logging
import re

from dsapy import app
from dsapy import flag

import jflow
from jflow import run
from jflow import branch


_logger = logging.getLogger(__name__)


class Resolve(app.Command):
    '''Resolve a branch family name into a latest branch name.'''
    name='resolve'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'name',
            metavar='NAME',
            help='Name to resolve',
        )

    def main(self):
        resolved = branch.Branch.resolve(self.flags.name)
        if resolved:
            print(resolved.branch)


if __name__ == '__main__':
    app.start()
