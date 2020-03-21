#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""List branches."""

import logging
import pprint
import re

from dsapy import app

import jflow
from jflow import branch
from jflow import color
from jflow import common
from jflow import config
from jflow import git
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class ListCmd(branch.TreeBuilder, app.Command):
    '''List branches.'''
    name='list'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '-d', '--description',
            action='store_true',
            help='Print branch descriptions',
        )
        parser.add_argument(
            '-p', '--patch',
            action='store_true',
            help='Print patches',
        )

    def branch_marks(self, b):
        r = common.Struct(typ=' ', public=' ', remote=' ', debug=' ', description='', merged=' ', patches='')
        if b.jflow:
            r.typ = 'j'
        elif b.patches is not None:
            r.typ = 's'

        if b.public is not None or b.self_public:
            r.public = 'p'

        if b.remote is not None:
            r.remote = 'r'

        if b.debug is not None:
            r.debug = 'd'

        if b.merged:
            r.merged = 'M'

        r.name = ' {c.W}{b.name}{c.N}'.format(c=color.Colors, b=b)

        def patches(status):
            return [p for p in b.patches if p.status == status]

        def pn(p):
            if p.merged:
                return color.Colors.ul + p.patch
            return p.patch

        def j(ps, prefix=None, suffix=None):
            if ps:
                return (prefix or '') + ' '.join(pn(p) for p in ps) + (suffix or '')
            return ''

        if b.patches is not None and self.flags.patch:
            ss = [('applied', color.Colors.g), ('unapplied', color.Colors.y), ('hidden', color.Colors.K)]
            ps = [j(patches(s), p, color.Colors.N) for s, p in ss]
            ps = [p for p in ps if p]
            r.patches = ' (' + ' '.join(ps) + ')'

        if b.description is not None and self.flags.description:
            r.description = ' | ' + b.description

        return r

    def main(self):
        branches = self.branch_tree()

        for b in branches.values():
            print('{m.typ}{m.public}{m.remote}{m.debug}{m.merged}{m.name}{m.patches}{m.description}'.format(
                b=b,
                m=self.branch_marks(b),
                c=color.Colors,
            ))
