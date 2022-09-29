#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import List, Dict, TypeVar, Type, Optional, Generic, overload, Union, Callable, Protocol

import functools

from dsapy.algs import strconv

from jf import git


class Error(Exception):
    '''Base for errors in the module.'''


SEPARATOR = '.'


class Holder(Protocol):
    @property
    def config(self) -> Dict[str, List[str]]:
        raise NotImplementedError

    def set(self, name: str, value: str) -> None:
        raise NotImplementedError

    def reset(self, name: str, value: str) -> None:
        raise NotImplementedError

    def append(self, name: str, value: str) -> None:
        raise NotImplementedError

    def unset(self, name: str) -> None:
        raise NotImplementedError


class Cfg:
    def __init__(self, cfg: Holder) -> None:
        self.cfg = cfg

    @property
    def raw(self) -> Dict[str, List[str]]:
        return self.cfg.config


class Path:
    def __init__(self, path: List[str]) -> None:
        self.path_list = path

    @functools.cached_property
    def path(self) -> str:
        return SEPARATOR.join(self.path_list)


class CfgPath(Cfg, Path):
    def __init__(self, base: 'CfgPath', path: List[str]) -> None:
        Cfg.__init__(self, base.cfg)
        Path.__init__(self, base.path_list + path)


class SectionCfg(CfgPath):
    @functools.cached_property
    def keys(self) -> List[str]:
        prefix = self.path + SEPARATOR
        return list({
            k[len(prefix):].partition(SEPARATOR)[0]
            for k in self.raw.keys()
            if k.startswith(prefix)
        })


TValue = TypeVar('TValue')


class ValueType(Protocol[TValue]):
    def from_string(self, s: str) -> TValue:
        raise NotImplementedError

    def to_string(self, v: TValue) -> str:
        raise NotImplementedError


class _SimpleType(Generic[TValue], ValueType[TValue]):
    def __init__(self, t: Callable[[str], TValue]) -> None:
        self.t = t

    def from_string(self, s: str) -> TValue:
        return self.t(s)

    def to_string(self, v: TValue) -> str:
        return str(v)


class _BoolType(ValueType[bool]):
    def from_string(self, s: str) -> bool:
        return strconv.parse_bool(s)

    def to_string(self, v: bool) -> str:
        return str(v).lower()


StrType = _SimpleType(str)
BranchType = _SimpleType(git.BranchName)
IntType = _SimpleType(int)
BoolType = _BoolType()


class MaybeValueCfg(Generic[TValue], CfgPath):
    def __init__(self, base: CfgPath, path: List[str], t: ValueType[TValue]) -> None:
        CfgPath.__init__(self, base, path)
        self.t = t

    @functools.cached_property
    def value(self) -> Optional[TValue]:
        v_list = self.raw.get(self.path, [])
        if not v_list:
            return None
        return self.t.from_string(v_list[0])

    def set(self, value: TValue) -> None:
        self.cfg.set(self.path, self.t.to_string(value))

    def set_str(self, s: str) -> None:
        self.set(self.t.from_string(s))

    def unset(self) -> None:
        self.cfg.unset(self.path)


class ValueCfg(Generic[TValue], CfgPath):
    def __init__(self, base: CfgPath, path: List[str], t: ValueType[TValue], default: TValue) -> None:
        CfgPath.__init__(self, base, path)
        self.t = t
        self.default = default

    @functools.cached_property
    def value(self) -> TValue:
        v_list = self.raw.get(self.path, [])
        if not v_list:
            return self.default
        return self.t.from_string(v_list[0])

    def set(self, value: TValue) -> None:
        self.cfg.set(self.path, self.t.to_string(value))

    def set_str(self, s: str) -> None:
        self.set(self.t.from_string(s))


class ListValueCfg(Generic[TValue], CfgPath):
    def __init__(self, base: CfgPath, path: List[str], t: ValueType[TValue]) -> None:
        CfgPath.__init__(self, base, path)
        self.t = t

    @functools.cached_property
    def value(self) -> List[TValue]:
        return [self.t.from_string(v) for v in self.raw.get(self.path, [])]

    def set(self, value: List[TValue]) -> None:
        if not value:
            self.cfg.unset(self.path)
            return
        self.cfg.reset(self.path, self.t.to_string(value[0]))
        for v in value[1:]:
            self.cfg.append(self.path, self.t.to_string(v))

    def append(self, value: TValue) -> None:
        self.cfg.append(self.path, self.t.to_string(value))

    def set_str(self, ss: List[str]) -> None:
        self.set([self.t.from_string(s) for s in ss])

    def append_str(self, s: str) -> None:
        self.append(self.t.from_string(s))


class MapCfg(Generic[TValue], SectionCfg):
    def __init__(
            self,
            base: CfgPath,
            path: List[str],
            factory: Callable[[CfgPath, List[str]], TValue],
    ) -> None:
        SectionCfg.__init__(self, base, path)
        self.factory = factory

    def __getitem__(self, name: str) -> TValue:
        return self.factory(self, [name])


_NOT_FOUND = object()

TCacher = TypeVar('TCacher', bound='Cacher')


class SchemaField:
    '''Base class to indicate schema fields.'''


class Cacher(Generic[TCacher, TValue], SchemaField):
    def __init__(self: TCacher) -> None:
        self.attrname = ''

    def __set_name__(self: TCacher, owner: type, name: str) -> None:
        if not self.attrname:
            self.attrname = name
        elif name != self.attrname:
            raise TypeError(
                "Cannot assign the same Cacher to two different names "
                f"({self.attrname!r} and {name!r})."
            )

    @overload
    def __get__(self: TCacher, instance: None, owner: type) -> TCacher:
        pass

    @overload
    def __get__(self: TCacher, instance: SectionCfg, owner: type) -> TValue:
        pass

    def __get__(self: TCacher, instance: Optional[SectionCfg], owner: type) -> Union[TCacher, TValue]:
        if instance is None:
            return self

        cache = instance.__dict__
        val = cache.get(self.attrname, _NOT_FOUND)
        if val is _NOT_FOUND:
            val = self.generate(instance)
            cache[self.attrname] = val
        return val

    def generate(self: TCacher, instance: SectionCfg) -> TValue:
        raise NotImplementedError


TSectionCfg = TypeVar('TSectionCfg', bound='SectionCfg')


class Section(Generic[TSectionCfg], Cacher['Section', TSectionCfg]):
    def __init__(self, t: Type[TSectionCfg], path: List[str]) -> None:
        Cacher.__init__(self)
        self.t = t
        self.path = path

    def generate(self, instance: SectionCfg) -> TSectionCfg:
        return self.t(instance, self.path)


class MaybeValue(Generic[TValue], Cacher['MaybeValue', MaybeValueCfg[TValue]]):
    def __init__(self, t: ValueType[TValue], path: List[str]) -> None:
        Cacher.__init__(self)
        self.t = t
        self.path = path

    def generate(self, instance: SectionCfg) -> MaybeValueCfg[TValue]:
        return MaybeValueCfg(instance, self.path, self.t)


class Value(Generic[TValue], Cacher['Value', ValueCfg[TValue]]):
    def __init__(self, t: ValueType[TValue], path: List[str], default: TValue) -> None:
        Cacher.__init__(self)
        self.t = t
        self.default = default
        self.path = path

    def generate(self, instance: SectionCfg) -> ValueCfg[TValue]:
        return ValueCfg(instance, self.path, self.t, self.default)


class ListValue(Generic[TValue], Cacher['ListValue', ListValueCfg[TValue]]):
    def __init__(self, t: ValueType[TValue], path: List[str]) -> None:
        Cacher.__init__(self)
        self.t = t
        self.path = path

    def generate(self, instance: SectionCfg) -> ListValueCfg[TValue]:
        return ListValueCfg(instance, self.path, self.t)


class Map(Generic[TValue], Cacher['Map', MapCfg[TValue]]):
    def __init__(self, factory: Callable[[CfgPath, List[str]], TValue], path: List[str]) -> None:
        Cacher.__init__(self)
        self.factory = factory
        self.path = path

    def generate(self, instance: SectionCfg) -> MapCfg[TValue]:
        return MapCfg(instance, self.path, self.factory)


class Root(SectionCfg):
    '''Config with schema.'''
    def __init__(self, cfg: Holder) -> None:
        self.cfg = cfg
        self.path_list: List[str] = []
