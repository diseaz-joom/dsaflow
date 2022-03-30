#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""List branches (debug)."""

import collections
import csv
import enum
import hashlib
import logging
import pprint
import sys
import re

from dsapy import app
from dsapy import logs
from dsapy.algs import bdfs

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


HEAD_PREFIX = 'refs/heads/'
TAG_PREFIX = 'refs/tags/'
REMOTE_PREFIX = 'refs/remotes/'
GENERIC_PREFIX = 'refs/'

PATCH_PREFIX = 'refs/patches/'
STGIT_SUFFIX = '.stgit'
PATCH_LOG_SUFFIX = '.log'


class Kind(enum.Enum):
    unknown = enum.auto()

    head = enum.auto()
    tag = enum.auto()
    remote = enum.auto()

    # StGit
    stgit = enum.auto()
    patch = enum.auto()
    patch_log = enum.auto()


    @classmethod
    def from_refname(cls, ref_name):
        if ref_name.startswith(HEAD_PREFIX):
            if ref_name.endswith(STGIT_SUFFIX):
                return cls.stgit
            return cls.head
        if ref_name.startswith(TAG_PREFIX):
            return cls.tag
        if ref_name.startswith(REMOTE_PREFIX):
            return cls.remote
        if ref_name.startswith(PATCH_PREFIX):
            if ref_name.endswith(PATCH_LOG_SUFFIX):
                return cls.patch_log
            return cls.patch
        return cls.unknown


def gen_abbrevs(ref_name):
    for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
        if ref_name.startswith(prefix):
            short = ref_name[len(prefix):]
            for p in _gen_prefixes(prefix):
                yield p+short
            break


def _gen_prefixes(full_prefix):
    p = full_prefix
    while p:
        yield p
        p = p[p.find('/')+1:]
    yield p


def ref_short(ref_name):
    for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
        if ref_name.startswith(prefix):
            return ref_name[len(prefix):]
    return ref_name


class Commit(object):
    def __init__(self, sha, *, parents=None, refs=None, children=None):
        self.sha = sha
        self.parents = parents or []
        self.children = children or []
        self.refs = refs or []

    def __repr__(self):
        args=['sha={s.sha!r}'.format(s=self)]
        if self.parents:
            args.append('parents={s.parents!r}'.format(s=self))
        if self.children:
            args.append('children={s.children!r}'.format(s=self))
        if self.refs:
            args.append('refs={s.refs!r}'.format(s=self))
        return 'Commit({})'.format(', '.join(args))


class Ref(object):
    def __init__(self, name, sha):
        self.name = name
        self.sha = sha
        self.short = ref_short(name)
        self.kind = Kind.from_refname(name)

    def __repr__(self):
        return 'Ref({s.name!r}, {s.sha!r})'.format(s=self)


class CommitTree(run.Cmd):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.drop_cache()

    # list_* = produce a list of entities
    # gen_* = produce a generator of entities
    # dict_* = product a dict of entities
    # cache_* = produce and update a cache of a collection of entities
    # get_* = update a cache if needed and return a cached value

    def list_remotes(self):
        return self.cmd_output(['git', 'remote'])

    def drop_cache(self):
        self.__commits = None
        self.__dict_commits = None
        self.__refs = None
        self.__abbrevs = None

    def get_refs(self):
        return self.__refs or self.cache_refs()

    def cache_refs(self):
        self.__refs = self.gen_refs()
        return self.__refs

    def gen_refs(self):
        refs = {}
        for line in self.cmd_output(['git', 'show-ref']):
            sha, name = line.split(' ')
            ref = Ref(name, sha)
            refs[ref.name] = ref
        return refs

    def get_abbrevs(self):
        return self.__abbrevs or self.cache_abbrevs()

    def cache_abbrevs(self):
        self.__abbrevs = self.gen_abbrevs()
        return self.__abbrevs

    def gen_abbrevs(self):
        refs = collections.defaultdict(list)
        for ref in self.get_refs().values():
            for abbrev in gen_abbrevs(ref.name):
                refs[abbrev].append(ref)
        return dict(refs)

    def get_ref(self, name):
        abbrevs = self.get_abbrevs()
        refs = abbrevs[name]
        if len(refs) > 1:
            raise Exception('ambiguous ref name {!r} -> {!r}'.format(name, [r.name for r in refs]))
        return refs[0]

    def get_commits(self):
        return self.__commits or self.cache_commits()

    def cache_commits(self):
        self.__commits = self.gen_commits()
        return self.__commits

    def gen_commits(self):
        commits = {}

        refs_dict = self.get_abbrevs()

        commit = None
        for line in self.cmd_output(['git', 'rev-list', '--all', '--pretty=format:parents% P%nrefs% D']):
            key = line.split(' ', 1)
            if len(key) != 2:
                continue
            key, value = key
            if key == 'commit':
                if commit:
                    commits[commit.sha] = commit
                commit = Commit(sha=value.strip())
            elif key == 'parents':
                commit.parents = value.split(' ')
            elif key == 'refs':
                r2s = []
                r1s = value.split(', ')
                for r1 in r1s:
                    r1 = r1.split(' -> ')[-1]
                    tag_p='tag: '
                    if r1.startswith(tag_p):
                        r1 = TAG_PREFIX + r1[len(tag_p):]
                    refs = refs_dict[r1]
                    if len(refs) > 1:
                        raise Exception('ambiguous ref name {!r} -> {!r}'.format(r1, [r.name for r in refs]))
                    r2s.append(refs[0])
                commit.refs = r2s
        if commit:
            commits[commit.sha] = commit

        for commit in commits.values():
            for parent_sha in commit.parents:
                commits[parent_sha].children.append(commit.sha)

        return commits

    def is_merged(self, into, ref):
        commits = self.get_commits()
        start = self.get_ref(into).sha
        target = self.get_ref(ref).sha
        for commit_sha in bdfs.bfs(start, lambda c: commits[c].parents):
            commit = commits[commit_sha]
            if commit.sha == target:
                return True
        return False


class ListDebugCmd(CommitTree, app.Command):
    '''List branches debug.'''
    name='dlst'

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

    def main(self):
        for cmt in self.get_commits().values():
            print(cmt)


def make_hash(d):
    # h = hashlib.sha1()
    # h.update(d.encode('utf-8'))
    # return h.hexdigest()[:9]
    return d


class TaskDataCmd(CommitTree, app.Command):
    '''Produce a data for the task.'''
    name='task'

    def main(self):
        used_cmt = {}
        used_ref = {}

        w = csv.writer(sys.stdout)
        w.writerow(['commit','parents','refs'])
        for cmt in self.get_commits().values():
            cmt_hash = make_hash(cmt.sha)
            if cmt_hash in used_cmt:
                raise Exception('commit hash collision: %s = %s', used_cmt[cmt_hash], cmt.sha)
            used_cmt[cmt_hash] = cmt.sha

            ref_hashes = []
            for ref in cmt.refs:
                ref_hash = make_hash(ref.name)
                if ref_hash in used_ref:
                    raise Exception('ref hash collision: %s = %s', used_ref[ref_hash], ref)
                used_ref[ref_hash] = ref
                ref_hashes.append(ref_hash)

            w.writerow([
                cmt_hash,
                ' '.join(make_hash(p) for p in cmt.parents),
                ' '.join(ref_hashes),
            ])


class AbbrevsCmd(CommitTree, app.Command):
    '''List reference abbrevs.'''
    name='abbrevs'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'ref',
            help='Reference to abbreviate',
        )

    def main(self):
        for abbrev in gen_abbrevs(self.flags.ref):
            print(abbrev)


class RefsCmd(CommitTree, app.Command):
    '''List references.'''
    name='refs'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

    def main(self):
        for ref in self.get_refs().values():
            print('{r.kind.name} {r.short} -> {r.sha}'.format(r=ref))


class HeadsCmd(CommitTree, app.Command):
    '''List heads.'''
    name='heads'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

    def main(self):
        for ref in self.get_refs().values():
            if not ref.name.startswith(HEAD_PREFIX):
                continue
            print(ref)
