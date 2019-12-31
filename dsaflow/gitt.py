#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Program description."""

import collections
import enum
import itertools
import locale
import logging
import os
import re
import subprocess
import sys
from typing import *

from dsapy import app
from dsapy import flag

from dsaflow import pdict


_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


class Error(Exception):
    '''Base class for errors in the module.'''


T = TypeVar('T')

InOutT = int
READ: InOutT = subprocess.PIPE
DEVNULL: InOutT = subprocess.DEVNULL


def tool_info(args: List[Text], check:bool=True, stdout:Optional[InOutT]=READ, stderr:Optional[InOutT]=None) -> subprocess.CompletedProcess:
    _logger.debug('Run: %r', args)
    return subprocess.run(args, encoding=_encoding, stdout=stdout, stderr=stderr, check=check, universal_newlines=True)


def tool_action(args: List[Text], check:bool=True, stdout:Optional[InOutT]=None, stderr:Optional[InOutT]=None) -> subprocess.CompletedProcess:
    _logger.debug('Run: %r', args)
    return subprocess.run(args, encoding=_encoding, stdout=stdout, stderr=stderr, check=check, universal_newlines=True)


class Str(str):
    """String with additional attributes.

    Some attributes have default value if not set explicitly, distinguished by name prefix:
    - b_* boolean attributes, default False
    - s_* string attributes, default ''
    """
    def __getattr__(self, name):
        if name.startswith('b_'):
            return False
        if name.startswith('s_'):
            return ''
        if name.startswith('ls_'):
            r = []
            setattr(self, name, r)
            return r
        if name.startswith('dc_'):
            r = {}
            setattr(self, name, r)
            return r
        return super().__getattr__(name)

    def full_repr(self):
        return '{}{!r}'.format(
            super().__repr__(),
            self.__dict__,
        )


ConfigType = MutableMapping[Text, Text]

class GitConfig(Dict[Text, Text]):
    def __init__(self) -> None:
        super().__init__()
        self._read()

    def _read(self) -> None:
        p = tool_info(['git', 'config', '--list'])
        for line in p.stdout.split('\n'):
            line = line.strip()
            if not line:
                continue
            k, v = line.split('=', 1)
            self[k] = v

    def __setitem__(self, name: Text, value: Text) -> None:
        tool_action(['git', 'config', '--local', str(name), str(value)])
        return super().__setitem__(name, value)

    def __delitem__(self, name: Text) -> None:
        tool_action(['git', 'config', '--local', '--unset', str(name)])
        return super().__delitem__(name)

DefaultGitConfig = GitConfig()


V = TypeVar('V')
class DictView(MutableMapping[Text, V], Generic[V]):
    def __init__(self, dct: MutableMapping[Text, V], prefix:Text='') -> None:
        self.dct = dct
        self.prefix = prefix or ''

    def _name(self, name: Text) -> Text:
        return self.prefix + name

    def __getitem__(self, name: Text) -> V:
        return self.dct[self._name(name)]

    def __setitem__(self, name: Text, value: V) -> None:
        self.dct[self._name(name)] = value

    def __delitem__(self, name: Text) -> None:
        del self.dct[self._name(name)]

    def __len__(self) -> int:
        return (take_last(enumerate(self.keys(), 1)) or (0, 0))[0]

    def __bool__(self) -> bool:
        for k in self:
            return True
        return False

    def __iter__(self) -> Iterator[Text]:
        skeys = (
            strip_prefix_r(self.prefix, k)
            for k in self.dct.keys()
        )
        return (
            k
            for k, stripped in skeys
            if stripped
        )


class BranchKind(enum.Enum):
    Local = 0
    Public = 1
    Stgit = 2
    Remote = 3
    Patch = 4


# Information about branch
#
# Local branch naming scheme:
# <type_prefix><basename><local_suffix>
#
# type_prefix defines a branch. It defines what branch to fork from, what
# branches to merge into and some other behaviors.
#
# type_prefix is resoved into branch_type using git config. Having a key
# dsaflow.type.<branch_type>.prefix with type_prefix of the branch, the behavior
# is defined by other configuration keys under dsaflow.type.<branch_type>.
class BranchInfo(object):
    def __init__(
            self,
            name:Text,
            kind:BranchKind=BranchKind.Local,
            base:Optional[Text]=None,
            branch_type:Optional[Text]=None,
            branch_basename:Optional[Text]=None,
            stgit_name:Optional[Text]=None,
            local_suffix:Optional[Text]=None,
            public_name:Optional[Text]=None,
            public_prefix:Optional[Text]=None,
            public_suffix:Optional[Text]=None,
            **kw:Dict[Text,Any],
    ) -> None:
        super().__init__(**kw)
        # Branch name
        self.name = name
        self.kind = kind

        # Suffix for local branch name
        self.local_suffix = local_suffix or ''

        # Branch type
        self.branch_type = branch_type or ''

        # Basename of the branch
        self.branch_basename = branch_basename or ''

        # Name of StGit branch (technical branch need not be displayed)
        self.stgit_name = stgit_name or ''
        self.stgit_branch = None

        # Name of the public branch
        self.public_name = public_name or ''
        self.public_prefix = public_prefix or ''
        self.public_suffix = public_suffix or ''

        # Base branch (what the branch was forked from)
        self.base = base or ''

    def names(self) -> List[Text]:
        return non_empty([
            self.name,
            self.public_name,
            self.stgit_name,
        ])

    def __repr__(self) -> Text:
        props = self.__dict__.copy()
        name = props.pop('name')
        prop_pairs = sorted((k, v) for k, v in props.items() if v)
        prop_texts = ['{}={!r}'.format(k, v) for k, v in prop_pairs]
        args = [repr(name)] + prop_texts
        return 'BranchInfo({})'.format(', '.join(args))


class FlowConfig(object):
    """Base class for type checking."""


class ConfigConstV1(FlowConfig):
    Version = '1'

    GitBranchPx = 'branch.'

    StgitSx = '.stgit'
    StgitVersion = '2'
    StgitVersionKey = 'stgit.stackformatversion'

    DsaflowPx = 'dsaflow.'

    RepoPx = DsaflowPx + 'repo.'
    TypePx = DsaflowPx + 'type.'
    RefPx = DsaflowPx + 'ref.'
    BranchPx = DsaflowPx + 'branch.'

    BaseKey = 'fork-from'
    PublicPrefixKey = 'public-prefix'
    PublicSuffixKey = 'public-suffix'
    LocalSuffixKey = 'local-suffix'
    VersionKey = 'version'

    BranchBaseSx = '.' + BaseKey
    BranchPublicPrefixSx = '.' + PublicPrefixKey
    BranchPublicSuffixSx = '.' + PublicSuffixKey
    BranchLocalSuffixSx = '.' + LocalSuffixKey
    BranchVersionSx = '.' + VersionKey
    BranchSxByKey = {
        BaseKey: BranchBaseSx,
        PublicPrefixKey: BranchPublicPrefixSx,
        PublicSuffixKey: BranchPublicSuffixSx,
        LocalSuffixKey: BranchLocalSuffixSx,
    }

    RefNameSx = ''

    RepoUrlSx = ''

    BranchBaseDf = 'develop'
    BranchPublicPrefixDf = 'feature'
    BranchPublicSuffixDf = ''
    BranchLocalSuffixDf = 'local'
    BranchDfCfg = {
        BaseKey: BranchBaseDf,
        PublicPrefixKey: BranchPublicPrefixDf,
        PublicSuffixKey: BranchPublicSuffixDf,
        LocalSuffixKey: BranchLocalSuffixDf,
    }

    PrefixDelim = '/'
    SuffixDelim = '.'
    ConfigDelim = '.'

    def __init__(self, git_cfg:ConfigType, **kw:Dict[Text,Any]) -> None:
        super().__init__(**kw)
        self.git_cfg = git_cfg

    def get_branch_config(self, branch_name:Text) -> ConfigType:
        return DictView(self.git_cfg, prefix=self.BranchPx + branch_name + self.ConfigDelim)

    def parse_branch_name(self, branch_name:Text) -> Tuple[Text, Text, Text]:
        """Parses branch name into (type, basename, local_suffix)."""
        branch_type, branch_local_name = split_exact(branch_name, self.PrefixDelim, 1, dir=Dir.Left)
        local_suffix = self.branch_cfg_value(branch_name, self.LocalSuffixKey) or ''
        basename, has_local_suffix = strip_suffix_r(self.SuffixDelim + local_suffix, branch_local_name)
        return branch_type, basename, (local_suffix if has_local_suffix else '')

    def public_branch_name(self, branch_name:Text) -> Text:
        """Builds public branch name."""
        branch_type, basename, _ = self.parse_branch_name(branch_name)
        public_prefix = self.branch_cfg_value(branch_name, self.PublicPrefixKey)
        public_suffix = self.branch_cfg_value(branch_name, self.PublicSuffixKey)
        return self.PrefixDelim.join(non_empty([public_prefix, self.SuffixDelim.join(non_empty([basename, public_suffix]))]))

    def stgit_branch_name(self, branch_name:Text) -> Text:
        return branch_name + self.StgitSx

    def branch_base(self, branch_name:Text) -> Optional[Text]:
        """Returns base branch name for an existing branch.

        Returns None if base branch cannot be determined.
        """
        return self.get_branch_config(branch_name).get(self.BaseKey)

    def fill_branch_names(self, b:Any, branch_name:Text) -> Any:
        branch_type, branch_local_name = split_exact(branch_name, self.PrefixDelim, 1, dir=Dir.Left)
        local_suffix = self.branch_cfg_value(branch_name, self.LocalSuffixKey) or ''
        branch_basename, has_local_suffix = strip_suffix_r(self.SuffixDelim + local_suffix, branch_local_name)
        if has_local_suffix:
            local_suffix = self.SuffixDelim + local_suffix
        public_prefix = self.branch_cfg_value(branch_name, self.PublicPrefixKey) or ''
        if public_prefix:
            public_prefix = public_prefix + self.PrefixDelim
        public_suffix = self.branch_cfg_value(branch_name, self.PublicSuffixKey) or ''
        if public_suffix:
            public_suffix = self.SuffixDelim + public_suffix
        public_name = public_prefix + branch_basename + public_suffix
        stgit_name = self.stgit_branch_name(branch_name)

        if branch_type:
            b.s_type = branch_type
        if branch_basename:
            b.s_basename = branch_basename
        if local_suffix:
            b.s_local_suffix = local_suffix
        if public_prefix:
            b.s_public_prefix = public_prefix
        if public_suffix:
            b.s_public_suffix = public_suffix
        b.s_public_name = public_name
        b.s_stgit_name = stgit_name
        b.names = set(non_empty([branch_name, public_name, stgit_name]))

    def get_branch_info(self, branch_name:Text, full=True) -> BranchInfo:
        branch_type, branch_local_name = split_exact(branch_name, self.PrefixDelim, 1, dir=Dir.Left)
        local_suffix = self.branch_cfg_value(branch_name, self.LocalSuffixKey) or ''
        branch_basename, has_local_suffix = strip_suffix_r(self.SuffixDelim + local_suffix, branch_local_name)
        if has_local_suffix:
            local_suffix = self.SuffixDelim + local_suffix
        public_prefix = self.branch_cfg_value(branch_name, self.PublicPrefixKey) or ''
        if public_prefix:
            public_prefix = public_prefix + self.PrefixDelim
        public_suffix = self.branch_cfg_value(branch_name, self.PublicSuffixKey) or ''
        if public_suffix:
            public_suffix = self.SuffixDelim + public_suffix

        public_name = public_prefix + branch_basename + public_suffix
        has_public = (public_name == branch_name)
        if full and not has_public:
            has_public = branch_exists(public_name)
        stgit_version = self.branch_stgit_version(branch_name)
        return BranchInfo(
            name=branch_name,
            base=self.branch_base(branch_name),
            branch_type=branch_type,
            branch_basename=branch_basename,
            stgit_name=self.stgit_branch_name(branch_name),
            local_suffix=local_suffix,
            public_name=public_name,
            public_prefix=public_prefix,
            public_suffix=public_suffix,
            stgit_version=stgit_version,
            dsaflow_version=self.branch_dsaflow_version(branch_name),
            has_public=has_public,
            has_stgit=bool(stgit_version),
        )

    def branch_cfg_value(self, branch_name:Text, name:Text, default:Optional[Text]=None) -> Optional[Text]:
        # Look for value in branch config
        value = self.get_branch_config(branch_name).get(name)
        if value is not None:
            return value

        # If missing in branch config, look in type config
        base_type, _ = split_exact(branch_name, self.PrefixDelim, 1, dir=Dir.Left)
        type_cfg = DictView(self.git_cfg, prefix=self.TypePx + base_type + self.ConfigDelim)
        value = type_cfg.get(name)
        if value is not None:
            return value

        # If default was provided, return it
        if default is not None:
            return default

        # Else look in global defaults
        default_cfg = self.BranchDfCfg
        return default_cfg.get(name)

    def branch_stgit_version(self, branch_name:Text) -> Optional[Text]:
        branch_cfg = DictView(self.git_cfg, prefix=self.GitBranchPx + branch_name + self.ConfigDelim)
        return branch_cfg.get(self.StgitVersionKey)

    def branch_dsaflow_version(self, branch_name:Text) -> Optional[Text]:
        return self.get_branch_config(branch_name).get(self.VersionKey)

    def branch_all_names(self, branch_name:Text) -> List[Text]:
        r = [branch_name]
        if self.branch_stgit_version(branch_name):
            stgit_branch_name = self.stgit_branch_name(branch_name)
            if stgit_branch_name != branch_name:
                r.append(stgit_branch_name)

        if self.branch_dsaflow_version(branch_name):
            public_branch_name = self.public_branch_name(branch_name)
            if public_branch_name != branch_name:
                r.append(public_branch_name)

        return r

    def all_branches_grouped(self) -> List[List[Text]]:
        heads = all_heads()
        merges: Dict[Text, Text] = {}
        branches: Dict[Text, List[Text]] = {}
        for head in heads:
            if head in merges:
                continue
            bi = self.get_branch_info(head)
            bns = non_empty([bi.name, bi.stgit_name, bi.public_name])
            for i, b in enumerate(bns):
                merges[b] = head
                if b in branches:
                    del branches[b]
            branches[head] = []

        for head in heads:
            branches[merges[head]].append(head)

        return sorted(sorted(bns) for bns in branches.values())

    def all_branch_infos(self) -> List[BranchInfo]:
        heads = all_heads()
        merges: Dict[Text, Text] = {}
        branches: Dict[Text, BranchInfo] = {}
        for head in heads:
            if head in merges:
                continue
            bi = self.get_branch_info(head)
            bns = non_empty([bi.name, bi.stgit_name, bi.public_name])
            for b in bns:
                merges[b] = head
                if b in branches:
                    del branches[b]
            branches[head] = bi

        return sorted(branches.values(), key=lambda b: b.name)

    def all_branches_grouped2(self) -> List[List[Text]]:
        return sorted(sorted(non_empty([b.name, b.public_name if b.has_public else '', b.stgit_name if b.has_stgit else ''])) for b in self.all_branch_infos())


DefaultConfig = ConfigConstV1(git_cfg=DefaultGitConfig)


class Dir(enum.Enum):
    Left = 0
    Right = 1


def split_exact(s:Text, d:Text, n:int, default:Text='', dir:Dir=Dir.Left) -> List[Text]:
    sm = s.split if dir == Dir.Left else s.rsplit
    ss = sm(d, n)
    m = n + 1 - len(ss)
    if m > 0:
        p = [default] * m
        return (ss + p if dir else p + ss)
    return ss


def non_empty(it: Iterable[Optional[T]]) -> List[T]:
    return [x for x in it if x]


def strip_prefix_r(prefix: Text, s: Text) -> Tuple[Text, bool]:
    if s.startswith(prefix):
        return s[len(prefix):], True
    return s, False


def strip_suffix_r(suffix: Text, s: Text) -> Tuple[Text, bool]:
    if s.endswith(suffix):
        return s[:len(s)-len(suffix)], True
    return s, False


def strip_prefix(prefix: Text, s: Text) -> Text:
    return strip_prefix_r(prefix, s)[0]


def strip_suffix(suffix: Text, s: Text) -> Text:
    return strip_suffix_r(suffix, s)[0]


def take_last(it: Iterable[T]) -> Optional[T]:
    r = None
    for r in it:
        pass
    return r


def branch_exists(branch_name: Text) -> bool:
    p = tool_info(['git', 'rev-parse', '--verify', '--quiet', branch_name], check=False)
    return p.returncode == os.EX_OK


def all_heads() -> List[Text]:
    p = tool_info(['git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads/**'])
    return [head.strip() for head in p.stdout.split('\n') if head.strip()]
