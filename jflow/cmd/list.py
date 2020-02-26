#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Publish a branch."""

import logging
import pprint
import re

from dsapy import app

import jflow
from jflow import common
from jflow import config
from jflow import git
from jflow import run
from jflow import struct


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class ListCmd(git.Git, run.Cmd, app.Command):
    '''List branches.'''
    name='list'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

    HEAD_RE = re.compile('refs/heads/(?P<name>.*)')
    REMOTE_RE = re.compile('refs/remotes/(?P<remote>[^/]+)/(?P<name>.*)')
    TAG_RE = re.compile('refs/tags/(?P<name>.*)')
    PATCH_RE = re.compile('refs/patches/(?P<name>.*)/(?P<patch>[^/]+)')
    PATCHLOG_RE = re.compile('refs/patches/(?P<name>.*)/(?P<patch>[^/]+)(?P<log>\.log)')

    def parse_ref(self, ref):
        for fmt, r in (('branch', self.HEAD_RE), ('remote', self.REMOTE_RE), ('tag', self.TAG_RE), ('patch', self.PATCH_RE), ('patchlog', self.PATCHLOG_RE)):
            m = r.match(ref)
            if not m:
                continue
            d = m.groupdict()
            d['fmt'] = fmt
            return d
        return {}

    def for_each_ref(self):
        for_each_ref_out = self.cmd_output(['git', 'for-each-ref', '--format=%(refname)'])
        for ref in for_each_ref_out:
            r = common.Struct(ref=ref)
            r.update(self.parse_ref(ref))
            yield r

    MARK_STATUS = {
        '+': 'applied',
        '>': 'applied',
        '-': 'unapplied',
        '!': 'hidden',
    }

    def stgit_patches(self, b, refs):
        patch_lines = self.cmd_output(['stg', 'series', '--all', '--branch={}'.format(b.name)])
        for line in patch_lines:
            mark, patch_name = line.split(' ', 1)
            status = self.MARK_STATUS[mark]
            patch_ref = 'refs/patches/{b}/{p}'.format(b=b.name, p=patch_name)
            patch_b = refs[patch_ref]
            patch_b.update({
                'patch': patch_name,
                'status': status,
            })
            yield patch_b

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
        refs = {r.ref:r for r in self.for_each_ref()}
        branches = {r.name:r for r in refs.values() if r.fmt == 'branch'}
        remotes = {r.name:r for r in refs.values() if r.fmt == 'remote'}

        cfg = dict(self.git_config_values())

        # Attach .stgit branches to their parents
        for b in list(branches.values()):
            key = config.branch_key_stgit_version(b.name)
            if key not in cfg:
                continue
            stgit_key = config.branch_stgit_name(b.name)
            stgit_b = branches.pop(stgit_key, None)
            if stgit_b is None:
                continue
            b.stgit = stgit_b
            b.patches = list(self.stgit_patches(b, refs))

        # Extract jflow branches
        for b in list(branches.values()):
            key = config.branch_key_version(b.name)
            if key not in cfg:
                continue
            b.jflow = True

        # Attach related branches to jflow
        for b in list(branches.values()):
            remote_name = b.name
            remote_b = remotes.pop(remote_name, None)
            if remote_b is not None:
                b.remote = remote_b

            # if not b.jflow:
            #     continue

            public_key = config.branch_key_public(b.name)
            public_name = cfg.get(public_key)
            public_b = branches.pop(public_name, None)
            if public_b is not None:
                b.public = public_b

            debug_key = config.branch_key_debug(b.name)
            debug_name = cfg.get(debug_key)
            debug_b = remotes.pop(debug_name, None)
            if debug_b is not None:
                b.debug = debug_b


        # Attach branch descriptions
        for b in branches.values():
            key = config.branch_key_description(b.name)
            description = cfg.get(key)
            if description is None:
                continue
            b.description = description

        for b in branches.values():
            print('{m.typ}{m.public}{m.remote}{m.debug} {b.name}{m.description}'.format(
                b=b,
                m=self.branch_marks(b),
            ))
