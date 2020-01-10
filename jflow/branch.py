#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Branch class."""

import logging
import re

import jflow
from jflow import run


_logger = logging.getLogger(__name__)


class Branch(object):
    FOR_EACH_REF_SEP = re.compile('\\s+')

    PREFIX_HEAD = 'refs/heads/'
    PREFIX_REMOTE = 'refs/remotes/'
    PREFIX_PATCH = 'refs/patches/'

    SUFFIX_STGIT = '.stgit'
    SUFFIX_LOG = '.log'
    SUFFIX_LOCAL = '.local'

    RE_REF = re.compile('(?P<prefix>{head}|{remote}|{patch})(?P<name>.*)$'.format(
        head=PREFIX_HEAD,
        remote=PREFIX_REMOTE,
        patch=PREFIX_PATCH,
    ))
    RE_REMOTE = re.compile('(?P<remote>[^/]+)/(?P<name>.*)$')
    RE_PATCH = re.compile('(?P<branch>.*)/(?P<patch>[^/]+)$')


    def __init__(self, remote=None, branch=None, patch=None, sha=None, log=None, stgit=None, remotes=None, patches=None, public=None, is_log=False, is_local=False, is_stgit=False, ref_full=None):
        self.remote = remote # Remote name (None for local branches)
        self.branch = branch # Base branch name (with .local and .stgit suffixes stripped)
        self.patch = patch # Patch name (with .log suffix stripped)
        self.sha = sha # Commit hash

        self.log = log # Log branch (for stgit patch refs)
        self.stgit = stgit # Stgit metadata branch
        self.remotes = remotes or [] # Remote branches for this branch
        self.patches = patches or [] # Patch branches
        self.public = public # Public branch (stg publish)

        self.is_log = is_log # Is this branch a log branch
        self.is_local = is_local # Is this branch a local branch
        self.is_stgit = is_stgit # Is this branch an stgit metadata branch
        self.ref_full = ref_full # Full ref name

    @classmethod
    def make(cls, ref_name, ref_hash=None):
        m = cls.RE_REF.match(ref_name)
        if not m:
            return None

        prefix = m.group('prefix')
        remote = None
        branch = m.group('name')
        patch = None
        is_log = False
        is_local = False
        is_stgit = False

        if prefix == cls.PREFIX_REMOTE:
            mr = cls.RE_REMOTE.match(branch)
            if not mr:
                return
            remote = mr.group('remote')
            branch = mr.group('name')
        elif prefix == cls.PREFIX_PATCH:
            mr = cls.RE_PATCH.match(branch)
            if not mr:
                return
            branch = mr.group('branch')
            patch = mr.group('patch')
            if patch.endswith(cls.SUFFIX_LOG):
                patch, is_log = jflow.strip_suffix(cls.SUFFIX_LOG, patch)

        branch, is_stgit = jflow.strip_suffix(cls.SUFFIX_STGIT, branch)
        branch, is_local = jflow.strip_suffix(cls.SUFFIX_LOCAL, branch)

        r = cls(
            remote=remote, branch=branch, patch=patch,
            sha=ref_hash,
            ref_full=ref_name,
            is_log=is_log,
            is_local=is_local,
            is_stgit=is_stgit,
        )
        return r

    def __repr__(self):
        return repr(self.__dict__)

    def full_ref(self):
        prefix = self.PREFIX_HEAD
        remote = ''
        if self.remote:
            prefix = self.PREFIX_REMOTE
            remote = self.remote + '/'
        elif self.patch:
            prefix = self.PREFIX_PATCH

        branch = self.branch
        if self.is_local:
            branch += self.SUFFIX_LOCAL
        if self.is_stgit:
            branch += self.SUFFIX_STGIT

        patch = ''
        if self.patch:
            patch = '/' + self.patch

        if self.is_log:
            patch += self.SUFFIX_LOG

        return prefix + remote + branch + patch

    @classmethod
    def iter_heads(cls):
        refs = (cls.FOR_EACH_REF_SEP.split(line) for line in run.get_output(['git', 'for-each-ref']))
        for ref_hash, ref_type, ref_name in refs:
            if ref_type != 'commit':
                continue
            b = cls.make(ref_name, ref_hash=ref_hash)
            if not b:
                continue
            yield b

    @classmethod
    def iter_hier(cls):
        bs = {b.full_ref(): b for b in cls.iter_heads()}
        skip = set()
        for b in bs.values():
            pr, pt = b._get_parent_ref()
            pb = bs.get(pr)
            if not pb:
                continue
            skip.add(b._connect_parent(pb, pt))
        for b in bs.values():
            if b.full_ref() not in skip:
                yield b

    @staticmethod
    def version_less(a, b):
        if a is None:
            return True
        if not a:
            return False
        return a < b

    @classmethod
    def resolve(cls, name, heads=None):
        if heads is None:
            heads = cls.iter_hier()
        prefix = name + '/'
        resolved_key = None
        resolved = None
        for b in heads:
            branch_key, prefixed = jflow.strip_prefix(prefix, b.branch)
            if prefixed or b.branch == name:
                if cls.version_less(resolved_key, branch_key):
                    resolved_key, resolved = branch_key, b
        return resolved

    def _get_parent_ref(self):
        if self.remote:
            return Branch(branch=self.branch, patch=self.patch, is_local=self.is_local, is_stgit=self.is_stgit, is_log=self.is_log).full_ref(), 'remote'
        if self.is_log:
            return Branch(branch=self.branch, patch=self.patch, is_local=self.is_local, is_stgit=self.is_stgit).full_ref(), 'log'
        if self.patch:
            return Branch(branch=self.branch, is_local=self.is_local, is_stgit=self.is_stgit).full_ref(), 'patch'
        if self.is_stgit:
            return Branch(branch=self.branch, is_local=self.is_local).full_ref(), 'stgit'
        elif self.is_local:
            return Branch(branch=self.branch).full_ref(), 'local'
        return None, None

    def _connect_parent(self, p, pt):
        if pt == 'remote':
            p.remotes.append(self)
            return self.full_ref()
        elif pt == 'log':
            p.log = self
            return self.full_ref()
        elif pt == 'patch':
            p.patches.append(self)
            return self.full_ref()
        elif pt == 'stgit':
            p.stgit = self
            return self.full_ref()
        elif pt == 'local':
            self.public = p
            return p.full_ref()
