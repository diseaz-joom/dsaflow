#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import List, Dict, TypeVar, Type, Optional, Generator, Tuple

import collections
import functools

from dsapy.algs import strconv

from jf import command
from jf import schema


class Error(Exception):
    '''Base for errors in the module.'''


SEPARATOR = '.'


class JfTemplateCfg(schema.SectionCfg):
    '''Jflow template config.'''

    KEYS = [
        'version', 'upstream', 'fork',
        'lreview_prefix', 'lreview_suffix',
        'review_prefix', 'review_suffix',
        'ldebug_prefix', 'ldebug_suffix',
        'debug_prefix', 'debug_suffix',
    ]

    version = schema.Value(schema.IntType, ['version'], default=0)
    upstream = schema.MaybeValue(schema.StrType, ['upstream'])
    fork = schema.MaybeValue(schema.StrType, ['fork'])

    ldebug_prefix = schema.MaybeValue(schema.StrType, ['ldebug-prefix'])
    ldebug_suffix = schema.MaybeValue(schema.StrType, ['ldebug-suffix'])
    debug_prefix = schema.MaybeValue(schema.StrType, ['debug-prefix'])
    debug_suffix = schema.MaybeValue(schema.StrType, ['debug-suffix'])

    lreview_prefix = schema.MaybeValue(schema.StrType, ['public-prefix'])
    lreview_suffix = schema.MaybeValue(schema.StrType, ['public-suffix'])
    review_prefix = schema.MaybeValue(schema.StrType, ['remote-prefix'])
    review_suffix = schema.MaybeValue(schema.StrType, ['remote-suffix'])


class JfCfg(schema.SectionCfg):
    '''Section of global Jflow config.'''

    remote = schema.Value(schema.StrType, ['remote'], default='origin')
    template = schema.Map(JfTemplateCfg, ['template'])

    default_green = schema.ListValue(schema.StrType, ['default-green'])
    autosync = schema.Value(schema.BoolType, ['autosync'], default=False)


class JfBranchCfg(schema.SectionCfg):
    '''Jflow configuration for a branch.'''

    KEYS = [
        'version', 'remote',
        'upstream', 'fork',
        'lreview', 'review',
        'ldebug', 'debug',
        'hidden', 'protected', 'tested', 'sync',
        'debug_prefix', 'debug_suffix',
    ]

    version = schema.Value(schema.IntType, ['version'], default=0)
    remote = schema.MaybeValue(schema.StrType, ['remote-name'])

    upstream = schema.Value(schema.StrType, ['upstream'], '')
    fork = schema.Value(schema.StrType, ['fork'], '')

    ldebug = schema.MaybeValue(schema.StrType, ['ldebug'])
    debug = schema.MaybeValue(schema.StrType, ['debug'])
    lreview = schema.MaybeValue(schema.StrType, ['public'])
    review = schema.MaybeValue(schema.StrType, ['remote'])

    debug_prefix = schema.MaybeValue(schema.StrType, ['debug-prefix'])
    debug_suffix = schema.MaybeValue(schema.StrType, ['debug-suffix'])

    # Properties below are not only for jflow-controlled branches

    hidden = schema.Value(schema.BoolType, ['hidden'], default=False)
    protected = schema.Value(schema.BoolType, ['protected'], default=False)
    sync = schema.Value(schema.BoolType, ['sync'], default=False)

    tested = schema.MaybeValue(schema.StrType, ['tested'])


class StgitBranchCfg(schema.SectionCfg):
    '''Stgit configuration for a branch.'''

    version = schema.Value(schema.IntType, ['stackformatversion'], default=0)
    parentbranch = schema.MaybeValue(schema.StrType, ['parentbranch'])


class GitRemoteCfg(schema.SectionCfg):
    '''Remote configuration.'''

    url = schema.MaybeValue(schema.StrType, ['url'])


class GitBranchCfg(schema.SectionCfg):
    '''Branches configuration.'''

    jf = schema.Section(JfBranchCfg, ['jflow'])
    stgit = schema.Section(StgitBranchCfg, ['stgit'])
    remote = schema.Value(schema.StrType, ['remote'], default='')
    merge = schema.Value(schema.StrType, ['merge'], default='')
    description = schema.Value(schema.StrType, ['description'], default='')


class Root(schema.Root):
    def __init__(self) -> None:
        schema.Root.__init__(self, GitConfigHolder())

    branch = schema.Map(GitBranchCfg, ['branch'])
    remote = schema.Map(GitRemoteCfg, ['remote'])
    jf = schema.Section(JfCfg, ['jflow'])


class GitConfigHolder:
    def __init__(self) -> None:
        self._config: Optional[Dict[str, List[str]]] = None

    @property
    def config(self) -> Dict[str, List[str]]:
        if self._config is not None:
            return self._config
        self._config = collections.defaultdict(list)
        for name, value in self._gen_config():
            self._config[name].append(value)
        return self._config

    @staticmethod
    def _gen_config() -> Generator[Tuple[str, str], None, None]:
        for line in command.read(['git', 'config', '--list']):
            name, value = line.split('=', 1)
            yield name, value

    def set(self, name: str, value: str) -> None:
        command.run(['git', 'config', '--local', name, value])
        if self._config is None:
            return
        self._config[name] = [value]

    def reset(self, name: str, value: str) -> None:
        command.run(['git', 'config', '--local', '--replace-all', name, value])
        if self._config is None:
            return
        self._config[name] = [value]

    def append(self, name: str, value: str) -> None:
        command.run(['git', 'config', '--local', '--add', name, value])
        if self._config is None:
            return
        self._config[name].append(value)

    def unset(self, name: str) -> None:
        command.run(['git', 'config', '--local', '--unset-all', name])
        if self._config is None:
            return
        del self._config[name]


class V1(object):
    VERSION = 1

    @functools.lru_cache(maxsize=None)
    def branch(self, name: str) -> 'BranchKey':
        return BranchKey(cfg=self, parts=['branch', name])

    @functools.lru_cache(maxsize=None)
    def remote(self, name: str) -> 'RemoteKey':
        return RemoteKey(cfg=self, parts=['remote', name])

    @functools.cached_property
    def jf(self) -> 'JfKey':
        return JfKey(cfg=self, parts=['jflow'])

    @functools.cached_property
    def config(self) -> Dict[str, List[str]]:
        raw_config: Dict[str, List[str]] = collections.defaultdict(list)
        for name, value in gen_config():
            raw_config[name].append(value)
        return dict(raw_config)


KeyT = TypeVar('KeyT', bound='Key')


class Key:
    def __init__(self, cfg: 'V1' = None, parts: List[str] = None):
        self.cfg: V1 = cfg or V1()
        self.parts: List[str] = parts or []

    def __repr__(self) -> str:
        return 'Key({})'.format(
            ', '.join(repr(p) for p in self.parts),
        )

    @classmethod
    def copy(cls: Type[KeyT], k: 'Key') -> KeyT:
        return cls(cfg=k.cfg, parts=list(k.parts))

    @classmethod
    def append(cls: Type[KeyT], k: 'Key', *parts: str) -> KeyT:
        p = list(k.parts)
        p.extend(parts)
        return cls(cfg=k.cfg, parts=p)

    @functools.cached_property
    def key(self) -> str:
        return SEPARATOR.join(self.parts)

    def get(self, default: str = None) -> Optional[str]:
        v = self.cfg.config.get(self.key, None)
        if not v:
            return default
        return v[0]

    @functools.cached_property
    def value(self) -> Optional[str]:
        return self.get()

    @functools.cached_property
    def as_str(self) -> str:
        return self.get() or ''

    @functools.cached_property
    def as_int(self) -> int:
        return self.get_int() or 0

    @functools.cached_property
    def as_bool(self) -> bool:
        return self.get_bool()

    @functools.cached_property
    def as_list(self) -> List[str]:
        return self.get_list()

    def get_bool(self, default: bool = False) -> bool:
        if self.value is None:
            return default
        return strconv.parse_bool(self.value, default)

    def get_int(self, default: int = None) -> Optional[int]:
        if self.value is None:
            return default
        return int(self.value)

    def get_list(self, default: List[str] = None) -> List[str]:
        v = self.cfg.config.get(self.key, None)
        return v or default or []

    def set(self, value: str) -> None:
        command.run(['git', 'config', '--local', self.key, value])

    def set_list(self, value: List[str]) -> None:
        op = '--replace-all'
        for v in value:
            command.run(['git', 'config', '--local', op, self.key, v])
            op = '--add'

    def unset(self) -> None:
        command.run(['git', 'config', '--local', '--unset-all', self.key])


class BranchKey(Key):
    @functools.cached_property
    def jf(self) -> 'JfBranchKey':
        return JfBranchKey.append(self, 'jflow')

    @functools.cached_property
    def stgit(self) -> 'StgitBranchKey':
        return StgitBranchKey.append(self, 'stgit')

    @functools.cached_property
    def remote(self) -> Key:
        return Key.append(self, 'remote')

    @functools.cached_property
    def merge(self) -> Key:
        return Key.append(self, 'merge')

    @functools.cached_property
    def description(self) -> Key:
        return Key.append(self, 'description')


class JfBranchKey(Key):
    KEYS = [
        'version', 'remote',
        'review', 'public',
        'debug', 'ldebug',
        'upstream', 'fork',
        'hidden', 'protected', 'tested', 'sync',
        'debug_prefix', 'debug_suffix',
    ]

    @functools.cached_property
    def version(self) -> Key:
        return Key.append(self, 'version')

    @functools.cached_property
    def remote(self) -> Key:
        return Key.append(self, 'remote-name')

    @functools.cached_property
    def public(self) -> Key:
        return Key.append(self, 'public')

    @functools.cached_property
    def debug(self) -> Key:
        return Key.append(self, 'debug')

    @functools.cached_property
    def ldebug(self) -> Key:
        return Key.append(self, 'ldebug')

    @functools.cached_property
    def upstream(self) -> Key:
        return Key.append(self, 'upstream')

    @functools.cached_property
    def fork(self) -> Key:
        return Key.append(self, 'fork')

    @functools.cached_property
    def review(self) -> Key:
        return Key.append(self, 'remote')

    @functools.cached_property
    def debug_prefix(self) -> Key:
        return Key.append(self, 'debug-prefix')

    @functools.cached_property
    def debug_suffix(self) -> Key:
        return Key.append(self, 'debug-suffix')

    # Properties below are not only for jflow-controlled branches

    @functools.cached_property
    def hidden(self) -> Key:
        '''Exclude branch from all operations.

        Hidden branch will not be displayed in lists, will be excluded from
        massive operations.
        '''
        return Key.append(self, 'hidden')

    @functools.cached_property
    def protected(self) -> Key:
        return Key.append(self, 'protected')

    @functools.cached_property
    def tested(self) -> Key:
        '''Name of the "tested" branch.'''
        return Key.append(self, 'tested')

    @functools.cached_property
    def sync(self) -> Key:
        '''Update branch from upstream on sync.'''
        return Key.append(self, 'sync')


class StgitBranchKey(Key):
    @functools.cached_property
    def version(self) -> Key:
        return Key.append(self, 'stackformatversion')

    @functools.cached_property
    def parentbranch(self) -> Key:
        return Key.append(self, 'parentbranch')


class JfKey(Key):
    @functools.cached_property
    def templates_root(self) -> Key:
        return Key.append(self, 'template')

    @functools.lru_cache(maxsize=None)
    def template(self, prefix) -> 'JfTemplateKey':
        return JfTemplateKey.append(self.templates_root, prefix)

    @functools.cached_property
    def templates_list(self) -> List[str]:
        prefix = self.templates_root.key + '.'
        suffix = '.version'
        templates = []
        for key_name in self.cfg.config.keys():
            if not (key_name.startswith(prefix) and key_name.endswith(suffix)):
                continue
            templates.append(key_name[len(prefix):-len(suffix)])
        return templates

    @functools.cached_property
    def default_green(self) -> Key:
        return Key.append(self, 'default-green')

    @functools.cached_property
    def remote(self) -> Key:
        return Key.append(self, 'remote')

    @functools.cached_property
    def autosync(self) -> Key:
        return Key.append(self, 'autosync')


class RemoteKey(Key):
    @functools.cached_property
    def url(self) -> Key:
        return Key.append(self, 'url')


class JfTemplateKey(Key):
    KEYS = [
        'version', 'upstream', 'fork',
        'lreview_prefix', 'lreview_suffix',
        'review_prefix', 'review_suffix',
        'ldebug_prefix', 'ldebug_suffix',
        'debug_prefix', 'debug_suffix',
    ]

    @functools.cached_property
    def version(self) -> Key:
        return Key.append(self, 'version')

    @functools.cached_property
    def upstream(self) -> Key:
        return Key.append(self, 'upstream')

    @functools.cached_property
    def fork(self) -> Key:
        return Key.append(self, 'fork')

    @functools.cached_property
    def lreview_prefix(self) -> Key:
        return Key.append(self, 'public-prefix')

    @functools.cached_property
    def lreview_suffix(self) -> Key:
        return Key.append(self, 'public-suffix')

    @functools.cached_property
    def review_prefix(self) -> Key:
        return Key.append(self, 'remote-prefix')

    @functools.cached_property
    def review_suffix(self) -> Key:
        return Key.append(self, 'remote-suffix')

    @functools.cached_property
    def ldebug_prefix(self) -> Key:
        return Key.append(self, 'ldebug-prefix')

    @functools.cached_property
    def ldebug_suffix(self) -> Key:
        return Key.append(self, 'ldebug-suffix')

    @functools.cached_property
    def debug_prefix(self) -> Key:
        return Key.append(self, 'debug-prefix')

    @functools.cached_property
    def debug_suffix(self) -> Key:
        return Key.append(self, 'debug-suffix')


def gen_config() -> Generator[Tuple[str, str], None, None]:
    for line in command.read(['git', 'config', '--list']):
        name, value = line.split('=', 1)
        yield name, value
