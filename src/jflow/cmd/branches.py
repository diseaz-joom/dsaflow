#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""List branches."""

import logging
import pprint

from dsapy import app

from jflow import branch


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class BranchesCmd(branch.TreeBuilder, app.Command):
    '''List branches internal struct.'''
    name='branches'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

    def main(self):
        bs = self.branch_tree()
        pprint.pprint(bs)
