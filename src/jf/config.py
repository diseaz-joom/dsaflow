#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import List, Dict, Optional, Generator, Tuple

import collections

from jf import command
from jf import common
from jf import schema


class Error(Exception):
    '''Base for errors in the module.'''


SEPARATOR = schema.SEPARATOR


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

    upstream = schema.Value(schema.BranchType, ['upstream'], common.ZeroBranchName)
    fork = schema.Value(schema.BranchType, ['fork'], common.ZeroBranchName)

    ldebug = schema.MaybeValue(schema.BranchType, ['ldebug'])
    debug = schema.MaybeValue(schema.BranchType, ['debug'])
    lreview = schema.MaybeValue(schema.BranchType, ['public'])
    review = schema.MaybeValue(schema.BranchType, ['remote'])

    debug_prefix = schema.MaybeValue(schema.StrType, ['debug-prefix'])
    debug_suffix = schema.MaybeValue(schema.StrType, ['debug-suffix'])

    # Properties below are not only for jflow-controlled branches

    hidden = schema.Value(schema.BoolType, ['hidden'], default=False)
    protected = schema.Value(schema.BoolType, ['protected'], default=False)
    sync = schema.Value(schema.BoolType, ['sync'], default=False)

    tested = schema.MaybeValue(schema.BranchType, ['tested'])


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
