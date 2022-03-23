#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import *

import collections
import contextlib
import enum
import functools
import logging
import subprocess

from dsapy import app
from dsapy import flag
from dsapy import logs
from dsapy.algs import bdfs
from dsapy.algs import strconv

from jf import command
from jf import config


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base for errors in the module.'''


class AmbiguousRefNameError(Error):
    '''Short reference name matches more than one reference.'''


class NotImplementedError(Error):
    '''Not implemented.'''


class WorkdirIsNotCleanError(Error):
    '''Workdir is not clean.'''

    def __init__(self):
        return super('Workdir is not clean.')


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

_REMOTE_LOCAL = '.'
_REMOTE_ORIGIN = 'origin'


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
    def from_refname(cls, ref_name: str) -> 'Kind':
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


class Commit(object):
    def __init__(self, sha: str, *, refs: List[str] = None):
        self.sha = sha
        self.parents: List[str] = []
        self.children: List[str] = []
        self.refs: List[str] = refs or []

    def __repr__(self) -> str:
        args=['sha={s.sha!r}'.format(s=self)]
        if self.parents:
            args.append('parents={s.parents!r}'.format(s=self))
        if self.children:
            args.append('children={s.children!r}'.format(s=self))
        if self.refs:
            args.append('refs={s.refs!r}'.format(s=self))
        return 'Commit({})'.format(', '.join(args))

    def is_merged_into(self, gc: 'Cache', other: 'Commit') -> bool:
        return gc.is_merged_into(self.sha, other.sha)


class Ref(object):
    '''Represents a reference in repo.'''
    def __init__(self, name: str, sha: Optional[str]):
        self.name = name
        self.sha = sha

    @functools.cached_property
    def short(self) -> str:
        return ref_short(self.name)

    @functools.cached_property
    def kind(self) -> Kind:
        return Kind.from_refname(self.name)

    @functools.cached_property
    def remote(self) -> Optional[str]:
        if self.kind in (Kind.head, Kind.stgit):
            return _REMOTE_LOCAL
        if self.kind == Kind.remote:
            remote_name, _, _ = self.short.partition('/')
            return remote_name
        return None

    @functools.cached_property
    def branch_name(self) -> Optional[str]:
        if self.kind in (Kind.head, Kind.stgit):
            return self.short
        if self.kind == Kind.remote:
            _, _, branch_name = self.short.partition('/')
            return branch_name
        return None

    def __repr__(self) -> str:
        return 'Ref({s.name!r}, {s.sha!r})'.format(s=self)

    def is_merged_into(self, gc: 'Cache', other: 'Ref') -> bool:
        return gc.is_merged_into(self.sha, other.sha)

    @classmethod
    def branch_ref_name(cls, remote: str, branch_name: str) -> str:
        if remote == _REMOTE_LOCAL:
            return HEAD_PREFIX + branch_name
        return REMOTE_PREFIX + remote + '/' + branch_name

    @property
    def is_valid(self) -> bool:
        return bool(self.sha)


class PatchStatus(enum.Enum):
    unknown = enum.auto()

    applied = enum.auto()
    current = enum.auto()
    unapplied = enum.auto()
    hidden = enum.auto()

    @classmethod
    def from_stg_mark(cls, mark: str) -> 'PatchStatus':
        return STGIT_MARK.get(mark, PatchStatus.unknown)


STGIT_MARK: Dict[str, PatchStatus] = {
    '+': PatchStatus.applied,
    '>': PatchStatus.current,
    '-': PatchStatus.unapplied,
    '!': PatchStatus.hidden,
}


class PatchInfo(object):
    def __init__(
            self,
            ref: Ref,
            log_ref: Ref,
            status: PatchStatus,
    ):
        self.ref = ref
        self.log_ref = log_ref
        self.status = status

    @property
    def is_applied(self) -> bool:
        return self.status in (PatchStatus.applied, PatchStatus.current)

    @property
    def is_visible(self) -> bool:
        return self.status != PatchStatus.hidden


BranchT = TypeVar('BranchT', bound='Branch')


class Branch(object):
    def __init__(
            self,
            gc: 'Cache',
            ref: Ref,
    ):
        self.gc = gc
        self.ref = ref

    def __repr__(self):
        return 'Branch({})'.format(self.ref)

    @property
    def is_jflow(self) -> bool:
        return self.jflow_version is not None

    @property
    def is_stgit(self) -> bool:
        return self.stgit_version is not None

    @property
    def name(self) -> str:
        return self.ref.short

    def gen_related_refs(self) -> Generator[Ref, None, None]:
        if self.public:
            yield self.public
        if self.stgit:
            yield self.stgit

    @functools.cached_property
    def patches(self) -> List[PatchInfo]:
        if not self.is_jflow:
            return []

        result: List[PatchInfo] = []

        patch_prefix = PATCH_PREFIX + self.name + '/'
        patch_lines = command.read(['stg', 'series', '--all', '--branch={}'.format(self.name)])
        for line in patch_lines:
            mark, patch_name = line.split(' ', 1)
            status = PatchStatus.from_stg_mark(mark)
            patch_ref = self.gc.refs[patch_prefix + patch_name]
            patch_log_ref = self.gc.refs[patch_prefix + patch_name + PATCH_LOG_SUFFIX]
            result.append(PatchInfo(patch_ref, patch_log_ref, status))

        return result

    @functools.cached_property
    def public_branch_name(self) -> Optional[str]:
        if self.is_jflow:
            if self.jflow_version != 1:
                raise UnsupportedJflowVersionError(self.jflow_version)
        else:
            return None
        return self.gc.cfg.branch(self.name).jf().public().get()

    @functools.cached_property
    def public_ref_name(self) -> Optional[str]:
        if not self.public_branch_name:
            return None
        return Ref.branch_ref_name(_REMOTE_LOCAL, self.public_branch_name)

    @functools.cached_property
    def public(self) -> Optional[Ref]:
        if not self.public_ref_name:
            return None
        return self.gc.refs.get(self.public_ref_name, None)

    @functools.cached_property
    def debug_ref_name(self) -> Optional[str]:
        if self.is_jflow:
            if self.jflow_version != 1:
                raise UnsupportedJflowVersionError(self.jflow_version)
        else:
            return None
        debug_branch_name = self.gc.cfg.branch(self.name).jf().debug().get()
        if not debug_branch_name:
            return None
        return Ref.branch_ref_name(_REMOTE_ORIGIN, debug_branch_name)

    @functools.cached_property
    def debug(self) -> Optional[Ref]:
        if not self.debug_ref_name:
            return None
        return self.gc.refs.get(self.debug_ref_name, None)

    @functools.cached_property
    def jflow_version(self) -> Optional[int]:
        v = self.gc.cfg.branch(self.name).jf().version().get()
        if v is None:
            return None
        return int(v)

    @functools.cached_property
    def stgit_version(self) -> Optional[int]:
        v = self.gc.cfg.branch(self.name).stgit().version().get()
        if v is None:
            return None
        return int(v)

    @functools.cached_property
    def stgit(self) -> Optional[Ref]:
        return self.gc.refs.get(self.ref.name + STGIT_SUFFIX, None)

    @functools.cached_property
    def remote_ref_name(self) -> str:
        if self.is_jflow:
            if self.jflow_version == 1:
                remote_branch_name = self.gc.cfg.branch(self.name).jf().remote().get()
                return Ref.branch_ref_name(_REMOTE_ORIGIN, remote_branch_name)
            else:
                raise UnsupportedJflowVersionError(self.jflow_version)
        remote = self.gc.cfg.branch(self.name).remote().get(_REMOTE_LOCAL)
        merge_ref_name = self.gc.cfg.branch(self.name).merge().get()
        if merge_ref_name:
            merge_ref = Ref(merge_ref_name, None)
            merge_branch_name = merge_ref.short
        else:
            merge_branch_name = self.name
        return Ref.branch_ref_name(remote, merge_branch_name)

    @functools.cached_property
    def remote(self) -> Optional[Ref]:
        return self.gc.refs.get(self.remote_ref_name, None)

    @functools.cached_property
    def fork_ref_name(self) -> str:
        if self.is_jflow:
            if self.jflow_version == 1:
                fork_branch_name = self.gc.cfg.branch(self.name).jf().fork().get()
                fork_ref_name = Ref.branch_ref_name(_REMOTE_LOCAL, fork_branch_name)
                return fork_ref_name or self.upstream_ref_name
            else:
                raise UnsupportedJflowVersionError(self.jflow_version)
        return self.upstream_ref_name

    @functools.cached_property
    def fork(self) -> Optional[Ref]:
        return self.gc.refs.get(self.fork_ref_name, None)

    @functools.cached_property
    def fork_branch(self) -> Optional['Branch']:
        return self.gc.branch_by_ref.get(self.fork_ref_name, None)

    @functools.cached_property
    def upstream_ref_name(self) -> str:
        if self.is_jflow:
            if self.jflow_version == 1:
                upstream_branch_name = self.gc.cfg.branch(self.name).jf().upstream().get()
                upstream_ref_name = Ref.branch_ref_name(_REMOTE_LOCAL, upstream_branch_name)
            else:
                raise UnsupportedJflowVersionError(self.jflow_version)
        elif self.is_stgit:
            upstream_ref_name = self.gc.cfg.branch(self.name).stgit().parentbranch().get()
        else:
            remote = self.gc.cfg.branch(self.name).remote().get(_REMOTE_LOCAL)
            merge_ref_name = self.gc.cfg.branch(self.name).merge().get()
            if merge_ref_name:
                merge_ref = Ref(merge_ref_name, None)
                merge_branch_name = merge_ref.short
            else:
                merge_branch_name = self.name
            upstream_ref_name = Ref.branch_ref_name(remote, merge_branch_name)
        return upstream_ref_name

    @functools.cached_property
    def upstream(self) -> Optional[Ref]:
        return self.gc.refs.get(self.upstream_ref_name, None)

    @functools.cached_property
    def upstream_branch(self) -> Optional['Branch']:
        return self.gc.branch_by_ref.get(self.upstream_ref_name, None)

    @functools.cached_property
    def tested_branch_name(self) -> Optional[str]:
        return self.gc.cfg.branch(self.name).jf().tested().get()

    @functools.cached_property
    def tested_branch(self) -> Optional['Branch']:
        if not self.tested_branch_name:
            return None
        return self.gc.branches.get(self.tested_branch_name, None)

    @functools.cached_property
    def hidden(self) -> bool:
        return strconv.parse_bool(self.gc.cfg.branch(self.name).jf().hidden().get('no'))

    def set_hidden(self, value: bool = True):
        if value == self.hidden:
            return
        command.run(['git', 'config', '--local', self.gc.cfg.branch(self.name).jf().hidden().key(), str(value).lower()], check=True)

    def publish_local(self, msg: str = None, force_new=False):
        if self.name == self.public_branch_name:
            return
        if self.stgit:
            if force_new:
                command.run(['stg', 'branch', '--delete', '--force', self.public_branch_name])
            cmd = ['stg', 'publish']
            if msg:
                cmd.append(f'--message={msg}')
            cmd.append(self.public_branch_name)
            command.run(cmd)
            return
        raise NotImplementedError('Not implemented for non-stgit branches')


_TAG_P = 'tag: '


_cache_properties = {'cfg'}


class Cache(object):
    def __init__(self, cfg=None):
        self.cfg = cfg or config.V1()

    def reset(self):
        for k in self.__dict__.keys():
            if k in _cache_properties:
                continue
            delattr(self, k)

    @functools.cached_property
    def refs_list(self):
        return list(gen_refs())

    @functools.cached_property
    def refs_abbrevs(self) -> Dict[str, List[Ref]]:
        '''
        Generates dict {abbrevName:[refObjects]} for all refs in repository and all
        valid abbreviations of their names.

        There can be conflicts, so a single abbrevName may correspond to a more than
        one reference.
        '''
        refs = collections.defaultdict(list)
        for ref in self.refs_list:
            for abbrev in ref_abbrevs(ref.name):
                refs[abbrev].append(ref)
        return dict(refs)

    @functools.cached_property
    def refs(self) -> Dict[str, Ref]:
        '''Dictionary name -> ref with all references in the repo.

        Includes non-ambiguous reference name abbreviations.
        '''
        return {name: refs[0] for name, refs in self.refs_abbrevs.items() if len(refs) == 1}

    def get_ref(self, ref_name) -> Optional[Ref]:
        '''Gets a reference by its name.

        Raises:
        - AmbiguousRefNameError
        '''
        refs = self.refs_abbrevs.get(ref_name, None)
        if not refs:
            return None
        if len(refs) > 1:
            raise AmbiguousRefNameError('ambiguous ref name {!r} -> {!r}'.format(ref_name, [r.name for r in refs]))
        return refs[0]

    @functools.cached_property
    def commits(self) -> Dict[str, Commit]:
        '''Dictionary commitSha -> Commit with all commits in the repo.'''

        commits = {}
        commit = None
        for line in command.read(['git', 'rev-list', '--all', '--pretty=format:parents% P%nrefs% D']):
            key, _, value = line.partition(' ')
            if not value:
                continue
            if key == 'commit':
                commit = Commit(sha=value.strip())
                commits[commit.sha] = commit
            elif key == 'parents':
                if not commit:
                    raise Error('Unknown commit')
                commit.parents = value.split(' ')
            elif key == 'refs':
                refs = []
                for r in value.split(', '):
                    sname, _, rname = r.partition(' -> ')
                    rr = rname or sname
                    if rr.startswith(_TAG_P):
                        rr = TAG_PREFIX + r[len(_TAG_P):]
                    if rr not in self.refs:
                        _logger.debug('Missing reference: {!r} <- {!r}\n  line: {!r}\n  value:  {!r}\n  at {!r}'.format(rr, r, line, value, commit))
                    else:
                        refs.append(self.refs[rr].name)
                if not commit:
                    raise Error('Unknown commit')
                commit.refs = refs

        for commit in commits.values():
            for parent_sha in commit.parents:
                commits[parent_sha].children.append(commit.sha)

        return commits

    @functools.cached_property
    def branch_by_ref(self) -> Dict[str, Branch]:
        all_heads = {}
        for ref in self.refs_list:
            if ref.kind != Kind.head:
                continue
            all_heads[ref.name] = Branch(self, ref)

        branch_refs = all_heads.copy()
        for k, b in all_heads.items():
            for r in b.gen_related_refs():
                branch_refs.pop(r.name, None)

        return branch_refs

    @functools.cached_property
    def branch_by_abbrev(self) -> Dict[str, Branch]:
        result: Dict[str, Branch] = {}
        for b in self.branch_by_ref.values():
            for abbrev in ref_abbrevs(b.ref.name):
                result[abbrev] = b
        return result

    @functools.cached_property
    def branches(self) -> Dict[str, Branch]:
        return {b.name: b for b in self.branch_by_ref.values()}

    @functools.cached_property
    def current_ref(self):
        return self.refs.get(current_ref, Ref(current_ref, current_ref))

    def is_merged_into(self, parent_sha: Optional[str], child_sha: Optional[str]) -> bool:
        start = [parent_sha]
        def exits(c):
            return self.commits[c].children if c else []
        for commit_sha in bdfs.dfs(start, exits):
            if commit_sha == child_sha:
                return True
        return False


def is_workdir_clean():
    return not command.read(['git', 'status', '--porcelain', '--untracked-files=no'])


def check_workdir_is_clean():
    if is_workdir_clean():
        return
    raise WorkdirIsNotCleanError()


_DEREFERENCE_SUFFIX = '^{}'

def gen_refs():
    '''Generates all refs in repo.'''
    refs_dict = {}

    head = 'HEAD'
    head_sha = command.read(['git', 'rev-parse', head])[0]
    yield Ref(head, head_sha)

    suffix_len = len(_DEREFERENCE_SUFFIX)
    for line in command.read(['git', 'show-ref', '--dereference']):
        sha, _, name = line.partition(' ')
        new_name = name
        deref = name.endswith(_DEREFERENCE_SUFFIX)
        if deref:
            new_name = name[:-suffix_len]
            refs_dict[new_name] = sha
        elif new_name not in refs_dict:
            refs_dict[new_name] = sha

    for name, sha in refs_dict.items():
        yield Ref(name, sha)


def ref_short(ref_name):
    '''Returns shortest valid abbreviation for full ref_name.'''
    for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
        if ref_name.startswith(prefix):
            return ref_name[len(prefix):]
    return ref_name


def ref_abbrevs(ref_name: str) -> List[str]:
    '''Builds valid abbreviation for full ref_name.'''
    result = []
    for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
        if ref_name.startswith(prefix):
            short = ref_name[len(prefix):]
            for p in _gen_prefixes(prefix):
                result.append(p+short)
            break
    return result or [ref_name]


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
    return Ref(current_ref, None).branch_name


current_branch = _get_current_branch()


def _gen_prefixes(full_prefix):
    '''Generates all possible abbreviated ref prefixes.'''
    p = full_prefix
    while p:
        yield p
        p = p[p.find('/')+1:]
    yield p


@contextlib.contextmanager
def detach_head():
    if not current_ref:
        raise Error('Undetected current ref')

    try:
        command.run(['git', 'checkout', '--detach', 'HEAD'])
        yield current_branch
    finally:
        command.run(['git', 'checkout', current_ref])
