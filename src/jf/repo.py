#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import List, Dict, Optional, Tuple, Generator

import collections
import enum
import functools
import logging

from dsapy.algs import bdfs

from jf import branch
from jf import command
from jf import config
from jf import git


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base for errors in the module.'''


_TAG_P = 'tag: '


_cache_properties = {'cfg'}


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
            ref: git.Ref,
            log_ref: git.Ref,
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


class Branch(branch.Generic):
    def __init__(
            self,
            gc: 'Cache',
            ref: git.Ref,
    ):
        super().__init__(gc.cfg, ref)
        self.gc = gc
        self.fullref = ref

    def __repr__(self):
        return 'Branch({})'.format(self.fullref)

    @functools.cached_property
    def generic(self) -> branch.Generic:
        return branch.Generic(self.gc.cfg, self.ref)

    @property
    def sha(self) -> git.Sha:
        return self.fullref.sha

    @functools.cached_property
    def patches(self) -> List[PatchInfo]:
        if not self.is_jflow:
            return []

        result: List[PatchInfo] = []

        patch_prefix = git.PATCH_PREFIX + self.name + '/'
        patch_lines = command.read(['stg', 'series', '--all', '--branch={}'.format(self.name)])
        for line in patch_lines:
            mark, patch_name = line.split(' ', 1)
            status = PatchStatus.from_stg_mark(mark)
            patch_ref = self.gc.refs[git.RefName(patch_prefix + patch_name)]
            patch_log_ref = self.gc.refs[git.RefName(patch_prefix + patch_name + git.PATCH_LOG_SUFFIX)]
            result.append(PatchInfo(patch_ref, patch_log_ref, status))

        return result

    @functools.cached_property
    def public_resolved(self) -> Optional[git.Ref]:
        ref_name = self.public
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def debug_resolved(self) -> Optional[git.Ref]:
        ref_name = self.debug
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def ldebug_resolved(self) -> Optional[git.Ref]:
        ref_name = self.ldebug
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def stgit_resolved(self) -> Optional[git.Ref]:
        ref_name = self.stgit
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def review_resolved(self) -> Optional[git.Ref]:
        ref_name = self.review
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def fork_resolved(self) -> Optional[git.Ref]:
        ref_name = self.fork
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def fork_branch(self) -> Optional['Branch']:
        r = self.fork_resolved
        if not r:
            return None
        return self.gc.branch_by_ref.get(r.name, None)

    @functools.cached_property
    def upstream_resolved(self) -> Optional[git.Ref]:
        ref_name = self.upstream
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def upstream_branch(self) -> Optional['Branch']:
        r = self.upstream_resolved
        if not r:
            return None
        return self.gc.branch_by_ref.get(r.name, None)

    @functools.cached_property
    def tested_resolved(self) -> Optional[git.Ref]:
        ref_name = self.tested
        if not ref_name:
            return None
        return self.gc.refs.get(ref_name, None)

    @functools.cached_property
    def tested_branch(self) -> Optional['Branch']:
        r = self.tested
        if not r:
            return None
        return self.gc.branch_by_ref.get(r, None)

    def publish_local_public(
            self, msg: str = None, force_new=False,
    ) -> Tuple[Optional[git.RefName], Optional[git.RefName]]:
        if not self.public or not self.public.branch:
            raise Error(f'No public branch for branch {self.name}')
        if self.name == self.public.branch:
            return self.public, self.review
        if not self.stgit_resolved:
            raise NotImplementedError('Not implemented for non-stgit branches')
        public_ref = self.public_resolved
        if force_new and public_ref:
            command.run(['stg', 'branch', '--delete', '--force', self.public.branch])
            public_ref = None
        if self.ldebug_resolved and (
            not public_ref or self.gc.is_merged_into(public_ref.sha, self.ldebug_resolved.sha)
        ):
            command.run(['git', 'branch', '--force', '--no-track', self.public.branch, self.ldebug_resolved])

        cmd = ['stg', 'publish']
        if msg:
            cmd.append(f'--message={msg}')
        cmd.append(self.public.branch)
        command.run(cmd)
        return self.public, self.review

    def publish_local_debug(
            self, msg: str = None, force_new=False,
    ) -> Tuple[Optional[git.RefName], Optional[git.RefName]]:
        if not self.ldebug or not self.ldebug.branch:
            raise Error(f'No local debug branch for branch {self.name}')
        if self.name == self.ldebug.branch:
            return self.ldebug, self.debug
        if not self.stgit_resolved:
            raise NotImplementedError('Not implemented for non-stgit branches')
        debug_ref = self.ldebug_resolved
        if force_new:
            if debug_ref:
                command.run(['stg', 'branch', '--delete', '--force', self.ldebug.branch])
                debug_ref = None
        elif self.public_resolved and (
            not debug_ref or self.gc.is_merged_into(debug_ref.sha, self.public_resolved.sha)
        ):
            command.run(['git', 'branch', '--force', '--no-track', self.ldebug.branch, self.public_resolved])

        cmd = ['stg', 'publish']
        if msg:
            cmd.append(f'--message={msg}')
        cmd.append(self.ldebug.branch)
        command.run(cmd)
        return self.ldebug, self.debug

    def publish_local(self, msg: str = None, force_new=False) -> Tuple[Optional[git.RefName], Optional[git.RefName]]:
        return self.publish_local_public(msg, force_new)


class Cache(object):
    def __init__(self, cfg: config.Root = None):
        self.cfg = cfg or config.Root()

    def reset(self):
        for k in self.__dict__.keys():
            if k in _cache_properties:
                continue
            delattr(self, k)

    @property
    def remote(self) -> str:
        return self.cfg.jf.remote.value or git.REMOTE_ORIGIN

    @functools.cached_property
    def refs_list(self) -> List[git.Ref]:
        return list(gen_refs())

    @functools.cached_property
    def refs_abbrevs(self) -> Dict[git.RefName, List[git.Ref]]:
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
    def refs(self) -> Dict[git.RefName, git.Ref]:
        '''Dictionary name -> ref with all references in the repo.

        Includes non-ambiguous reference name abbreviations.
        '''
        return {name: refs[0] for name, refs in self.refs_abbrevs.items() if len(refs) == 1}

    def get_ref(self, ref_name) -> git.Ref:
        '''Gets a reference by its name.

        Raises:
        - AmbiguousRefNameError
        '''
        refs = self.refs_abbrevs[ref_name]
        if len(refs) > 1:
            raise Error('ambiguous ref name {!r} -> {!r}'.format(ref_name, [r.name for r in refs]))
        return refs[0]

    @functools.cached_property
    def commits(self) -> Dict[git.Sha, git.Commit]:
        '''Dictionary commitSha -> Commit with all commits in the repo.'''

        commits = {}
        commit = None
        for line in command.read(['git', 'rev-list', '--all', '--pretty=format:parents% P%nrefs% D']):
            key, _, value = line.partition(' ')
            if not value:
                continue
            if key == 'commit':
                commit = git.Commit(sha=git.Sha(value.strip()))
                commits[commit.sha] = commit
            elif key == 'parents':
                if not commit:
                    raise Error('Unknown commit')
                commit.parents = [git.Sha(v) for v in value.split(' ')]
            elif key == 'refs':
                refs = []
                for r in value.split(', '):
                    sname, _, rname = r.partition(' -> ')
                    rr = git.RefName(rname or sname)
                    if rr.startswith(_TAG_P):
                        rr = git.RefName(git.TAG_PREFIX + r[len(_TAG_P):])
                    if rr not in self.refs:
                        _logger.debug(
                            (f'Missing reference: {rr!r} <- {r!r}\n'
                             '  line: {line!r}\n'
                             '  value:  {value!r}\n'
                             '  at {commit!r}'))
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
    def branch_by_ref(self) -> Dict[git.RefName, Branch]:
        all_heads = {}
        for ref in self.refs_list:
            if ref.kind != git.Kind.head:
                continue
            all_heads[ref.name] = Branch(self, ref)

        branch_refs = all_heads.copy()
        for k, b in all_heads.items():
            for r in b.gen_related_refs():
                branch_refs.pop(r, None)

        return branch_refs

    @functools.cached_property
    def branch_by_abbrev(self) -> Dict[str, Branch]:
        result: Dict[str, Branch] = {}
        for b in self.branch_by_ref.values():
            for abbrev in ref_abbrevs(b.ref):
                result[abbrev] = b
        return result

    @functools.cached_property
    def branches(self) -> Dict[str, Branch]:
        return {b.name: b for b in self.branch_by_ref.values()}

    @functools.lru_cache(maxsize=None)
    def resolve_shortcut(self, shortcut: str) -> Optional[git.Ref]:
        matches = []
        prefix = shortcut + '/'
        for r in self.refs_list:
            if not r.branch:
                continue
            if r.branch == shortcut:
                return r
            if r.branch.startswith(prefix):
                matches.append(r)
        if not matches:
            return None
        return max(matches, key=lambda r: (r.branch, r.is_remote))

    @functools.cached_property
    def current_ref(self) -> git.Ref:
        if not git.current_ref:
            raise Error('Not in git repo')
        return self.get_ref(git.current_ref)

    def is_merged_into(self, parent_sha: Optional[git.Sha], child_sha: Optional[git.Sha]) -> bool:
        if not parent_sha or not child_sha:
            return False

        start = [parent_sha]

        def exits(c):
            return self.commits[c].children

        for commit_sha in bdfs.dfs(start, exits):
            if commit_sha == child_sha:
                return True
        return False


def ref_abbrevs(ref_name: git.RefName) -> List[git.RefName]:
    '''Builds valid abbreviation for full ref_name.'''
    result = []
    for prefix in (git.HEAD_PREFIX, git.TAG_PREFIX, git.REMOTE_PREFIX, git.GENERIC_PREFIX):
        if ref_name.startswith(prefix):
            short = ref_name[len(prefix):]
            for p in _gen_prefixes(prefix):
                result.append(git.RefName(p+short))
            break
    return result or [ref_name]


def _gen_prefixes(full_prefix: str) -> Generator[git.RefName, None, None]:
    '''Generates all possible abbreviated ref prefixes.'''
    p = full_prefix
    while p:
        yield git.RefName(p)
        p = p[p.find('/')+1:]
    yield git.RefName(p)


_DEREFERENCE_SUFFIX = '^{}'


def gen_refs() -> Generator[git.Ref, None, None]:
    '''Generates all refs in repo.'''
    refs_dict = {}

    head = 'HEAD'
    head_sha = git.Sha(command.read(['git', 'rev-parse', head])[0])
    yield git.Ref(head, head_sha)

    suffix_len = len(_DEREFERENCE_SUFFIX)
    for line in command.read(['git', 'show-ref', '--dereference']):
        sha_str, _, name = line.partition(' ')
        sha = git.Sha(sha_str)

        new_name = name
        deref = name.endswith(_DEREFERENCE_SUFFIX)
        if deref:
            new_name = name[:-suffix_len]
            refs_dict[new_name] = sha
        elif new_name not in refs_dict:
            refs_dict[new_name] = sha

    for name, sha in refs_dict.items():
        yield git.Ref(name, sha)
