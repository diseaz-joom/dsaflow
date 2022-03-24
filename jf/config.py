#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import *

import collections
import functools

from dsapy.algs import strconv

from jf import command


class Error(Exception):
    '''Base for errors in the module.'''


SEPARATOR = '.'


class V1(object):
    VERSION=1

    def branch(self, name: str) -> 'BranchKey':
        return BranchKey.make(self, ['branch', name])

    def jf_branch(self, name: str) -> 'JfBranchKey':
        return self.branch(name).jf()

    def stgit_branch(self, name: str) -> 'StgitBranchKey':
        return self.branch(name).stgit()

    def jf(self) -> 'JfKey':
        return JfKey.make(self, ['jflow'])

    # @functools.cached_property
    # def config(self) -> Dict[str, str]:
    #     return dict(gen_config())

    @functools.cached_property
    def config(self) -> Dict[str, Union[str, List[str]]]:
        raw_config: Dict[str, List[str]] = collections.defaultdict(list)
        for name, value in gen_config():
            raw_config[name].append(value)
        result: Dict[str, Union[str, List[str]]] = {}
        for name, values in raw_config.items():
            if len(values) == 1:
                result[name] = values[0]
                continue
            result[name] = values
        return result


KeyT = TypeVar('KeyT', bound='Key')

class Key(object):
    def __init__(self, k: 'Key' = None, *, config: 'V1' = None, parts: List[str] = None):
        self.config: V1 = config or (k.config if k else V1())
        self.parts: List[str] = parts or []
        if not parts and k:
            self.parts = k.parts

    def __repr__(self) -> str:
        return 'Key({})'.format(
            ', '.join(repr(p) for p in self.parts),
        )

    @classmethod
    def make(cls: Type[KeyT], config: 'V1', parts: List[str]) -> KeyT:
        return cls(config=config, parts=parts)

    @classmethod
    def join(cls: Type[KeyT], k1: 'Key', k2: 'Key') -> KeyT:
        return cls(k1, parts=k1.parts + k2.parts)

    @classmethod
    def append(cls: Type[KeyT], k: 'Key', *parts: str) -> KeyT:
        return cls(k, parts=k.parts + list(parts))

    def key(self) -> str:
        return SEPARATOR.join(self.parts)

    def get(self, default: str = None) -> Optional[str]:
        v = self.config.config.get(self.key(), default)
        if isinstance(v, list):
            return v[0]
        return v

    def get_bool(self, default: bool = False) -> bool:
        v = self.get()
        if v is None:
            return default
        return strconv.parse_bool(v, default)

    def get_int(self, default: int = None) -> Optional[int]:
        v = self.get()
        if v is None:
            return default
        return int(v)

    def get_list(self, default: List[str] = None) -> List[str]:
        v = self.config.config.get(self.key(), default)
        if isinstance(v, list):
            return v
        elif v:
            return [v]
        return []

    def set(self, value: str) -> None:
        command.run(['git', 'config', '--local', self.key(), value])

    def unset(self) -> None:
        command.run(['git', 'config', '--unset', self.key()])


class BranchKey(Key):
    def jf(self) -> 'JfBranchKey':
        return JfBranchKey.append(self, 'jflow')

    def stgit(self) -> 'StgitBranchKey':
        return StgitBranchKey.append(self, 'stgit')

    def remote(self) -> Key:
        return Key.append(self, 'remote')

    def merge(self) -> Key:
        return Key.append(self, 'merge')


class JfBranchKey(Key):
    def version(self) -> Key:
        return Key.append(self, 'version')

    def public(self) -> Key:
        return Key.append(self, 'public')

    def debug(self) -> Key:
        return Key.append(self, 'debug')

    def upstream(self) -> Key:
        return Key.append(self, 'upstream')

    def fork(self) -> Key:
        return Key.append(self, 'fork')

    def remote(self) -> Key:
        return Key.append(self, 'remote')

    # Properties below are not only for jflow-controlled branches

    def hidden(self) -> Key:
        '''Exclude branch from all operations.

        Hidden branch will not be displayed in lists, will be excluded from
        massive operations.
        '''
        return Key.append(self, 'hidden')

    def tested(self) -> Key:
        '''Name of the "tested" branch.'''
        return Key.append(self, 'tested')

    def sync(self) -> Key:
        '''Update branch from upstream on sync.'''
        return Key.append(self, 'sync')

class StgitBranchKey(Key):
    def version(self) -> Key:
        return Key.append(self, 'stackformatversion')

    def parentbranch(self) -> Key:
        return Key.append(self, 'parentbranch')


class JfKey(Key):
    def template(self) -> Key:
        return JfTemplateKey.append(self, 'template')

    def default_green(self) -> Key:
        return Key.append(self, 'default-green')

    def origin(self) -> Key:
        return Key.append(self, 'origin')


class JfTemplateKey(Key):
    pass


def gen_config() -> Generator[Tuple[str, str], None, None]:
    for line in command.read(['git', 'config', '--list']):
        name, value = line.split('=', 1)
        yield name, value
