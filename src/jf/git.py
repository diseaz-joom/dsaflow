#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import contextlib
import enum
import functools
import logging
import subprocess
import typing as t

from jf import command
from jf import common


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base for errors in the module.'''


class WorkdirIsNotCleanError(Error):
    '''Workdir is not clean.'''

    def __init__(self):
        return super().__init__('Workdir is not clean.')


HEAD_PREFIX = 'refs/heads/'
TAG_PREFIX = 'refs/tags/'
REMOTE_PREFIX = 'refs/remotes/'
GENERIC_PREFIX = 'refs/'

PATCH_PREFIX = 'refs/patches/'
STGIT_SUFFIX = '.stgit'
PATCH_LOG_SUFFIX = '.log'

REMOTE_LOCAL = '.'
REMOTE_ORIGIN = 'origin'


class Kind(enum.Enum):
    unknown = enum.auto()

    head = enum.auto()
    tag = enum.auto()
    remote = enum.auto()

    # StGit
    stgit = enum.auto()
    patch = enum.auto()
    patch_log = enum.auto()


Sha = t.NewType('Sha', str)
ZeroSha = Sha('')


class BranchName(str):
    def __net__(cls, name):
        return super().__new__(cls, name)

    def ref(self, remote: str) -> 'RefName':
        if not self:
            return RefName('')

        if remote == REMOTE_LOCAL:
            return RefName(HEAD_PREFIX + self)
        return RefName(REMOTE_PREFIX + remote + '/' + self)


ZeroBranchName = BranchName('')


class RefName(str):
    '''Reference name manipulations.'''

    def __new__(cls, name):
        return super().__new__(cls, name)

    @property
    def is_valid(self) -> bool:
        return False

    @functools.cached_property
    def short(self) -> 'RefName':
        '''Returns shortest valid abbreviation for full ref_name.'''
        for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
            if self.startswith(prefix):
                return RefName(self[len(prefix):])
        return self

    @functools.cached_property
    def kind(self) -> Kind:
        if self.startswith(HEAD_PREFIX):
            if self.endswith(STGIT_SUFFIX):
                return Kind.stgit
            return Kind.head
        if self.startswith(TAG_PREFIX):
            return Kind.tag
        if self.startswith(REMOTE_PREFIX):
            return Kind.remote
        if self.startswith(PATCH_PREFIX):
            if self.endswith(PATCH_LOG_SUFFIX):
                return Kind.patch_log
            return Kind.patch
        return Kind.unknown

    @functools.cached_property
    def is_remote(self) -> bool:
        return self.kind == Kind.remote

    @functools.cached_property
    def remote(self) -> str:
        if self.kind == Kind.remote:
            remote_name, _, _ = self.short.partition('/')
            return remote_name
        return REMOTE_LOCAL

    @property
    def is_branch(self) -> bool:
        return self.kind in (Kind.head, Kind.stgit, Kind.remote)

    @functools.cached_property
    def branch(self) -> t.Optional[BranchName]:
        if self.kind in (Kind.head, Kind.stgit):
            return BranchName(self.short)
        if self.kind == Kind.remote:
            _, _, branch_name = self.short.partition('/')
            return BranchName(branch_name)
        return None


class Ref(RefName):
    '''Represents a reference in repo.'''

    def __init__(self, name: str, sha: Sha) -> None:
        self.sha = sha

    def __new__(cls, name: str, sha: Sha):
        common.check(sha, 'Invalid SHA for reference')
        v = super().__new__(cls, name)
        v.sha = sha
        return v

    def __repr__(self) -> str:
        r = str(self)
        return f'Ref({r!r}, {self.sha!r})'

    @property
    def is_valid(self) -> bool:
        return True

    @property
    def name(self) -> RefName:
        return RefName(self)


class Commit(object):
    def __init__(self, sha: Sha, *, refs: t.List[RefName] = None):
        self.sha = sha
        self.parents: t.List[Sha] = []
        self.children: t.List[Sha] = []
        self.refs: t.List[RefName] = refs or []

    def __repr__(self) -> str:
        args = ['sha={s.sha!r}'.format(s=self)]
        if self.parents:
            args.append('parents={s.parents!r}'.format(s=self))
        if self.children:
            args.append('children={s.children!r}'.format(s=self))
        if self.refs:
            args.append('refs={s.refs!r}'.format(s=self))
        return 'Commit({})'.format(', '.join(args))


def is_workdir_clean():
    return not command.read(['git', 'status', '--porcelain', '--untracked-files=no'])


def check_workdir_is_clean():
    if is_workdir_clean():
        return
    raise WorkdirIsNotCleanError()


def _get_current_ref() -> t.Optional[str]:
    cmd = ['git', 'symbolic-ref', '--quiet', 'HEAD']
    p = subprocess.run(cmd, stdout=subprocess.PIPE, check=False, encoding=command.ENCODING, universal_newlines=True)
    if p.stdout:
        return p.stdout.partition('\n')[0]

    cmd = ['git', 'rev-parse', 'HEAD']
    p = subprocess.run(cmd, stdout=subprocess.PIPE, check=False, encoding=command.ENCODING, universal_newlines=True)
    if p.stdout:
        return p.stdout.partition('\n')[0]

    return None


current_ref = _get_current_ref()


def _get_current_branch() -> t.Optional[str]:
    if not current_ref:
        return None
    return RefName(current_ref).branch


current_branch = _get_current_branch()


@contextlib.contextmanager
def detach_head():
    try:
        if current_branch:
            command.run(['git', 'checkout', '--detach', 'HEAD'])
        yield current_branch
    finally:
        if current_branch:
            command.run(['git', 'checkout', current_branch])
