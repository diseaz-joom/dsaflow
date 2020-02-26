#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Branch class."""

import logging
import re

import jflow
from jflow import common
from jflow import config
from jflow import git
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


class Controller(run.Cmd):
    Branch = Branch

    def branch_iter_heads(self):
        refs = (self.Branch.FOR_EACH_REF_SEP.split(line) for line in self.cmd_output(['git', 'for-each-ref']))
        for ref_hash, ref_type, ref_name in refs:
            if ref_type != 'commit':
                continue
            b = self.Branch.make(ref_name, ref_hash=ref_hash)
            if not b:
                continue
            yield b

    def branch_iter_tree(self):
        bs = {b.full_ref(): b for b in self.branch_iter_heads()}
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
    def branch_version_less(a, b):
        if a is None:
            return True
        if not a:
            return False
        return a < b

    def branch_resolve(self, name, heads=None):
        if not name:
            return None
        if heads is None:
            heads = self.branch_iter_tree()
        prefix = name + '/'
        resolved_key = None
        resolved = None
        for b in heads:
            branch_key, prefixed = jflow.strip_prefix(prefix, b.branch)
            if prefixed or b.branch == name:
                if self.branch_version_less(resolved_key, branch_key):
                    resolved_key, resolved = branch_key, b
        return resolved


class TreeBuilder(git.Git, run.Cmd):
    '''Builds branches tree.'''

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

    def branch_tree(self):
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

        # Find jflow branches
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

        return branches
