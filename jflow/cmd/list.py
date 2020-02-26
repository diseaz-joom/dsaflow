#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""List branches."""

import logging
import pprint
import re

from dsapy import app

import jflow
from jflow import branch
from jflow import common
from jflow import config
from jflow import git
from jflow import run
from jflow import struct


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class ListCmd(branch.TreeBuilder, app.Command):
    '''List branches.'''
    name='list'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

    def branch_marks(self, b):
        r = common.Struct(typ=' ', public=' ', remote=' ', debug=' ', description='')
        if b.jflow:
            r.typ = 'j'
        elif b.patches is not None:
            r.typ = 's'

        if b.public is not None:
            r.public = 'p'

        if b.remote is not None:
            r.remote = 'r'

        if b.debug is not None:
            r.debug = 'd'

        if b.description is not None:
            r.description = ' | ' + b.description

        return r

    def main(self):
        branches = self.branch_tree()

        for b in branches.values():
            print('{m.typ}{m.public}{m.remote}{m.debug} {b.name}{m.description}'.format(
                b=b,
                m=self.branch_marks(b),
            ))
