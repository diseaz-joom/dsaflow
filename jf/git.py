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


class RefName:
    '''Reference name manipulations.'''
    def __init__(self, name: str) -> None:
        self.name = name

    @staticmethod
    def for_branch(remote: str, branch_name: str) -> 'RefName':
        if remote == _REMOTE_LOCAL:
            return RefName(HEAD_PREFIX + branch_name)
        return RefName(REMOTE_PREFIX + remote + '/' + branch_name)

    def __repr__(self) -> str:
        return f'RefName({self.name!r})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RefName):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)

    @functools.cached_property
    def short(self) -> str:
        '''Returns shortest valid abbreviation for full ref_name.'''
        for prefix in (HEAD_PREFIX, TAG_PREFIX, REMOTE_PREFIX, GENERIC_PREFIX):
            if self.name.startswith(prefix):
                return self.name[len(prefix):]
        return self.name

    @functools.cached_property
    def kind(self) -> Kind:
        if self.name.startswith(HEAD_PREFIX):
            if self.name.endswith(STGIT_SUFFIX):
                return Kind.stgit
            return Kind.head
        if self.name.startswith(TAG_PREFIX):
            return Kind.tag
        if self.name.startswith(REMOTE_PREFIX):
            return Kind.remote
        if self.name.startswith(PATCH_PREFIX):
            if self.name.endswith(PATCH_LOG_SUFFIX):
                return Kind.patch_log
            return Kind.patch
        return Kind.unknown

    @functools.cached_property
    def is_remote(self) -> bool:
        return self.kind == Kind.remote

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


class Ref(RefName):
    '''Represents a reference in repo.'''
    def __init__(self, name: str, sha: str) -> None:
        super().__init__(name)
        self.sha = sha

    def __repr__(self) -> str:
        return f'Ref({self.name!r}, {self.sha!r})'

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

    def __init__(self, cfg: config.V1, ref: RefName):
        if not ref.branch_name:
            raise Error(f'Invalid branch ref: {ref.name}')
        self.cfg = cfg
        self.ref = ref

    def __repr__(self):
        return 'GenericBranch({})'.format(self.ref)

    @property
    def name(self) -> str:
        return self.ref.short

    @property
    def remote(self) -> str:
        return self.cfg.branch(self.name).jf.remote.as_str or self.cfg.jf.remote.as_str or _REMOTE_ORIGIN

    @property
    def is_jflow(self) -> bool:
        return bool(self.jflow_version)

    @functools.cached_property
    def jflow_version(self) -> int:
        return self.cfg.branch(self.name).jf.version.as_int

    @property
    def is_stgit(self) -> bool:
        return bool(self.stgit_version)

    @functools.cached_property
    def stgit_version(self) -> int:
        return self.cfg.branch(self.name).stgit.version.as_int

    @functools.cached_property
    def stgit_branch_name(self) -> Optional[str]:
        if not self.is_stgit:
            return None
        return self.name + STGIT_SUFFIX

    @functools.cached_property
    def stgit_name(self) -> Optional[RefName]:
        if not self.is_stgit:
            return None
        return RefName(self.ref.name + STGIT_SUFFIX)

    @functools.cached_property
    def public_branch_name(self) -> Optional[str]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            return self.cfg.branch(self.name).jf.public.value
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def public_name(self) -> Optional[RefName]:
        if not self.public_branch_name:
            return None
        return RefName.for_branch(_REMOTE_LOCAL, self.public_branch_name)

    @functools.cached_property
    def debug_branch_name(self) -> Optional[str]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            return self.cfg.branch(self.name).jf.debug.value
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def debug_name(self) -> Optional[RefName]:
        if not self.debug_branch_name:
            return None
        return RefName.for_branch(self.remote, self.debug_branch_name)

    @functools.cached_property
    def ldebug_branch_name(self) -> Optional[str]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            return self.cfg.branch(self.name).jf.ldebug.value
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def ldebug_name(self) -> Optional[RefName]:
        if not self.ldebug_branch_name:
            return None
        return RefName.for_branch(_REMOTE_LOCAL, self.ldebug_branch_name)

    @functools.cached_property
    def review_branch_name(self) -> Optional[str]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            return self.cfg.branch(self.name).jf.review.value
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def review_name(self) -> Optional[RefName]:
        if not self.review_branch_name:
            return None
        return RefName.for_branch(self.remote, self.review_branch_name)

    @functools.cached_property
    def upstream_branch_name(self) -> Optional[str]:
        ref = self.upstream_name
        if not ref:
            return None
        return ref.branch_name

    @functools.cached_property
    def upstream_name(self) -> Optional[RefName]:
        if not self.jflow_version:
            b = self.cfg.branch(self.name)
            if b.merge.value:
                return RefName.for_branch(b.remote.as_str, RefName(b.merge.as_str).branch_name)
            return None
        elif self.jflow_version == 1:
            return RefName.for_branch(_REMOTE_LOCAL, self.cfg.branch(self.name).jf.upstream.as_str)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def fork_branch_name(self) -> Optional[str]:
        ref = self.fork_name
        if not ref:
            return None
        return ref.branch_name

    @functools.cached_property
    def fork_name(self) -> Optional[RefName]:
        if not self.jflow_version:
            return self.upstream_name
        elif self.jflow_version == 1:
            name = self.cfg.branch(self.name).jf.fork.as_str
            if not name:
                return self.upstream_name
            return RefName.for_branch(_REMOTE_LOCAL, name)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def tested_branch_name(self) -> Optional[str]:
        return self.cfg.branch(self.name).jf.tested.value

    @functools.cached_property
    def tested_name(self) -> Optional[RefName]:
        if not self.tested_branch_name:
            return None
        return RefName.for_branch(_REMOTE_LOCAL, self.tested_branch_name)

    @functools.cached_property
    def sync(self) -> bool:
        if not self.jflow_version:
            if self.cfg.branch(self.name).jf.sync.as_bool:
                return True
            if not self.cfg.jf.autosync.as_bool:
                return False
            if not (self.upstream_name and self.upstream_name.is_remote):
                return False
            return True
        elif self.jflow_version == 1:
            return self.cfg.branch(self.name).jf.sync.as_bool
        raise UnsupportedJflowVersionError(self.jflow_version)

    def gen_related_refs(self) -> Generator[RefName, None, None]:
        if self.public_name and self.public_name != self.ref:
            yield self.public_name
        if self.ldebug_name and self.ldebug_name != self.ref:
            yield self.ldebug_name
        if self.stgit_name:
            yield self.stgit_name


class Branch(GenericBranch):
    def __init__(
            self,
            gc: 'Cache',
            ref: Ref,
    ):
        super().__init__(gc.cfg, ref)
        self.gc = gc
        self.fullref = ref

    def __repr__(self):
        return 'Branch({})'.format(self.fullref)

    @functools.cached_property
    def generic(self) -> GenericBranch:
        return GenericBranch(self.gc.cfg, self.ref)

    @property
    def sha(self) -> str:
        return self.fullref.sha

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
    def public(self) -> Optional[Ref]:
        ref_name = self.public_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def debug(self) -> Optional[Ref]:
        ref_name = self.debug_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def ldebug(self) -> Optional[Ref]:
        ref_name = self.ldebug_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def stgit(self) -> Optional[Ref]:
        ref_name = self.stgit_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def review(self) -> Optional[Ref]:
        ref_name = self.review_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def fork(self) -> Optional[Ref]:
        ref_name = self.fork_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def fork_branch(self) -> Optional['Branch']:
        r = self.fork
        if not r:
            return None
        return self.gc.branch_by_ref.get(r.name, None)

    @functools.cached_property
    def upstream(self) -> Optional[Ref]:
        ref_name = self.upstream_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def upstream_branch(self) -> Optional['Branch']:
        r = self.upstream
        if not r:
            return None
        return self.gc.branch_by_ref.get(r.name, None)

    @functools.cached_property
    def tested(self) -> Optional[Ref]:
        ref_name = self.tested_name
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name.name, None)

    @functools.cached_property
    def tested_branch(self) -> Optional['Branch']:
        r = self.tested_name
        if not r:
            return None
        return self.gc.branch_by_ref.get(r.name, None)

    @functools.cached_property
    def hidden(self) -> bool:
        return self.gc.cfg.branch(self.name).jf.hidden.as_bool

    @functools.cached_property
    def protected(self) -> bool:
        return self.gc.cfg.branch(self.name).jf.protected.as_bool

    def set_hidden(self, value: bool = True):
        if value == self.hidden:
            return
        command.run(['git', 'config', '--local', self.gc.cfg.branch(self.name).jf.hidden.key, str(value).lower()], check=True)

    @functools.cached_property
    def description(self) -> Optional[str]:
        return self.gc.cfg.branch(self.name).description.value

    def publish_local_public(self, msg: str = None, force_new=False) -> Tuple[Optional[RefName], Optional[RefName]]:
        if not self.public_branch_name:
            raise Error(f'No public branch for branch {self.name}')
        if self.name == self.public_branch_name:
            return self.public_name, self.review_name
        if not self.stgit:
            raise NotImplementedError('Not implemented for non-stgit branches')
        public_ref = self.public
        if force_new and public_ref:
            command.run(['stg', 'branch', '--delete', '--force', self.public_branch_name])
            public_ref = None
        if self.ldebug and (
            not public_ref or self.gc.is_merged_into(public_ref.sha, self.ldebug.sha)
        ):
            command.run(['git', 'branch', '--force', '--no-track', self.public_branch_name, self.ldebug.name])

        cmd = ['stg', 'publish']
        if msg:
            cmd.append(f'--message={msg}')
        cmd.append(self.public_branch_name)
        command.run(cmd)
        return self.public_name, self.review_name

    def publish_local_debug(self, msg: str = None, force_new=False) -> Tuple[Optional[RefName], Optional[RefName]]:
        if not self.ldebug_branch_name:
            raise Error(f'No local debug branch for branch {self.name}')
        if self.name == self.ldebug_branch_name:
            return self.ldebug_name, self.debug_name
        if not self.stgit:
            raise NotImplementedError('Not implemented for non-stgit branches')
        debug_ref = self.ldebug
        if force_new:
            if debug_ref:
                command.run(['stg', 'branch', '--delete', '--force', self.ldebug_branch_name])
                debug_ref = None
        elif self.public and (
            not debug_ref or self.gc.is_merged_into(debug_ref.sha, self.public.sha)
        ):
            command.run(['git', 'branch', '--force', '--no-track', self.ldebug_branch_name, self.public.name])

        cmd = ['stg', 'publish']
        if msg:
            cmd.append(f'--message={msg}')
        cmd.append(self.ldebug_branch_name)
        command.run(cmd)
        return self.ldebug_name, self.debug_name

    def publish_local(self, msg: str = None, force_new=False) -> Tuple[Optional[RefName], Optional[RefName]]:
        return self.publish_local_public(msg, force_new)


_TAG_P = 'tag: '


_cache_properties = {'cfg'}


class Cache(object):
    def __init__(self, cfg: config.V1 = None):
        self.cfg = cfg or config.V1()

    def reset(self):
        for k in self.__dict__.keys():
            if k in _cache_properties:
                continue
            delattr(self, k)

    @property
    def remote(self) -> str:
        return self.cfg.jf.remote.value or _REMOTE_ORIGIN

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

    def get_ref(self, ref_name) -> Ref:
        '''Gets a reference by its name.

        Raises:
        - AmbiguousRefNameError
        '''
        refs = self.refs_abbrevs[ref_name]
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

    @functools.lru_cache(maxsize=None)
    def resolve_shortcut(self, shortcut: str) -> Optional[Ref]:
        matches = []
        prefix = shortcut + '/'
        for r in self.refs_list:
            if not r.branch_name:
                continue
            if r.branch_name == shortcut:
                return r
            if r.branch_name.startswith(prefix):
                matches.append(r)
        if not matches:
            return None
        return max(matches, key=lambda r: (r.branch_name, r.is_remote))

    @functools.cached_property
    def current_ref(self) -> Ref:
        if not current_ref:
            raise Error('Not in git repo')
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
    return RefName(current_ref).branch_name


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
    try:
        if current_branch:
            command.run(['git', 'checkout', '--detach', 'HEAD'])
        yield current_branch
    finally:
        if current_branch:
            command.run(['git', 'checkout', current_branch])
