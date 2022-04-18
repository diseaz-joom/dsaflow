#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import List, Optional, Generator

import contextlib
import enum
import functools
import logging
import subprocess

from jf import command
from jf import common
from jf import config


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base for errors in the module.'''


class NotImplementedError(Error):
    '''Not implemented.'''


class WorkdirIsNotCleanError(Error):
    '''Workdir is not clean.'''

    def __init__(self):
        return super().__init__('Workdir is not clean.')


class UnsupportedJflowVersionError(Error):
    '''Unsupported Jflow version.'''

    def __init__(self, v):
        return super(f'Unsupported Jflow version: {v}')


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


Sha = common.Sha
ZeroSha = common.ZeroSha

BranchName = common.BranchName
ZeroBranchName = common.ZeroBranchName


# class BranchName(str):
#     def __net__(cls, name):
#         return super().__new__(cls, name)

#     def ref(self, remote: str) -> 'RefName':
#         if not self:
#             return RefName('')

#         if remote == REMOTE_LOCAL:
#             return RefName(HEAD_PREFIX + self)
#         return RefName(REMOTE_PREFIX + remote + '/' + self)


class RefName(str):
    '''Reference name manipulations.'''

    def __new__(cls, name):
        return super().__new__(cls, name)

    @staticmethod
    def for_branch(remote: str, branch_name: BranchName) -> 'RefName':
        if remote == REMOTE_LOCAL:
            return RefName(HEAD_PREFIX + branch_name)
        return RefName(REMOTE_PREFIX + remote + '/' + branch_name)

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
    def branch(self) -> Optional[BranchName]:
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
        r = repr(str(self))
        return f'Ref({r!r}, {self.sha!r})'

    @property
    def is_valid(self) -> bool:
        return True

    @property
    def name(self) -> RefName:
        return RefName(self)


class Commit(object):
    def __init__(self, sha: Sha, *, refs: List[RefName] = None):
        self.sha = sha
        self.parents: List[Sha] = []
        self.children: List[Sha] = []
        self.refs: List[RefName] = refs or []

    def __repr__(self) -> str:
        args = ['sha={s.sha!r}'.format(s=self)]
        if self.parents:
            args.append('parents={s.parents!r}'.format(s=self))
        if self.children:
            args.append('children={s.children!r}'.format(s=self))
        if self.refs:
            args.append('refs={s.refs!r}'.format(s=self))
        return 'Commit({})'.format(', '.join(args))


class GenericBranch:
    '''Branch is umbrella entity to describe logical branch.

    Logical branch includes several required physical branches.

        - Main branch, referenced by `ref` property is the branch in the local
          repository you directly work with.  It's usually under StGit control.

        - `upstream` is what main branch is logically tracks and eventually will
          be merged into.

        - `fork` is what main branch is physically forked from.  It may be
          different from upstream.  E.g. there may be a branch that follows
          upstream branch and only fast-forwards only if CI tests are passed.
          It's a good idea to put this branch as `fork`.

        - `stgit` branch is a technical branch for StGit.

        - `public` branch is a review-friendly branch in the local repository.
          With some configurations it can be the same as the main branch.
          Usually, for StGit-controlled branches `stg publish` builds public
          branch.

        - `review` is a branch in remote repository for review.  Usually it is a
          public branch pushed into remote repository.

        - `debug` is a branch in remote repository for running CI tests.

        - `ldebug` is a debug branch in the local repository.

        - `tested` branch is what new branches should be forked from by default
          if this branch is upstream.  It's not only for jflow-controlled
          branches.
    '''

    def __init__(self, cfg: config.Root, ref: RefName):
        if not ref.branch:
            raise Error(f'Invalid branch ref: {ref}')
        self.ref = ref
        self.cfg_root = cfg
        self.cfg = cfg.branch[self.name]

    def __repr__(self):
        return 'GenericBranch({})'.format(self.ref)

    @property
    def name(self) -> str:
        return self.ref.short

    @property
    def remote(self) -> str:
        return self.cfg.jf.remote.value or self.cfg.jf.remote.value or REMOTE_ORIGIN

    @functools.cached_property
    def description(self) -> str:
        return self.cfg.description.value

    @functools.cached_property
    def protected(self) -> bool:
        return self.cfg.jf.protected.value

    @functools.cached_property
    def hidden(self) -> bool:
        return self.cfg.jf.hidden.value

    @property
    def is_jflow(self) -> bool:
        return bool(self.jflow_version)

    @functools.cached_property
    def jflow_version(self) -> int:
        return self.cfg.jf.version.value

    @property
    def is_stgit(self) -> bool:
        return bool(self.stgit_version)

    @functools.cached_property
    def stgit_version(self) -> int:
        return self.cfg.stgit.version.value

    @functools.cached_property
    def stgit(self) -> Optional[RefName]:
        if not self.is_stgit:
            return None
        return RefName(self.ref + STGIT_SUFFIX)

    @functools.cached_property
    def public(self) -> Optional[RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            v = self.cfg.jf.lreview.value
            if not v:
                return None
            return RefName.for_branch(REMOTE_LOCAL, v)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def debug(self) -> Optional[RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            v = self.cfg.jf.debug.value
            if not v:
                return None
            return RefName.for_branch(self.remote, v)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def ldebug(self) -> Optional[RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            v = self.cfg.jf.ldebug.value or self.cfg.jf.debug.value
            if not v:
                return None
            return RefName.for_branch(REMOTE_LOCAL, v)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def review(self) -> Optional[RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            v = self.cfg.jf.review.value
            if not v:
                return None
            return RefName.for_branch(self.remote, v)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def upstream(self) -> Optional[RefName]:
        if not self.jflow_version:
            if not self.cfg.merge.value:
                return None
            br = RefName(self.cfg.merge.value)
            if not br.branch:
                return None
            return RefName.for_branch(self.cfg.remote.value, br.branch)
        elif self.jflow_version == 1:
            return RefName.for_branch(REMOTE_LOCAL, self.cfg.jf.upstream.value)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def fork(self) -> Optional[RefName]:
        if not self.jflow_version:
            return self.upstream
        elif self.jflow_version == 1:
            name = self.cfg.jf.fork.value
            if not name:
                return self.upstream
            return RefName.for_branch(REMOTE_LOCAL, name)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def tested(self) -> Optional[RefName]:
        branch_name = self.cfg.jf.tested.value
        if not branch_name:
            return None
        return RefName.for_branch(REMOTE_LOCAL, branch_name)

    @functools.cached_property
    def sync(self) -> bool:
        if self.is_jflow:
            return False
        if self.cfg.jf.sync.value:
            return True
        if not self.cfg_root.jf.autosync.value:
            return False
        if not (self.upstream and self.upstream.is_remote):
            return False
        return True

    def gen_related_refs(self) -> Generator[RefName, None, None]:
        if self.public and self.public != self.ref:
            yield self.public
        if self.ldebug and self.ldebug != self.ref:
            yield self.ldebug
        if self.stgit:
            yield self.stgit


def is_workdir_clean():
    return not command.read(['git', 'status', '--porcelain', '--untracked-files=no'])


def check_workdir_is_clean():
    if is_workdir_clean():
        return
    raise WorkdirIsNotCleanError()


def _get_current_ref() -> Optional[str]:
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


def _get_current_branch() -> Optional[str]:
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
