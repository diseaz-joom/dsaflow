#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from typing import Any, NewType

Sha = NewType('Sha', str)
ZeroSha = Sha('')

BranchName = NewType('BranchName', str)
ZeroBranchName = BranchName('')


class Struct(dict):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__dict__ = self

    @classmethod
    def from_dict(cls, d):
        return cls(d)

    def copy(self):
        return self.from_dict(self)

    def __getitem__(self, name):
        try:
            return super().__getitem__(name)
        except (AttributeError, KeyError):
            return None

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except (AttributeError, KeyError):
            return None


def check(condition: Any, msg: str = ''):
    if condition:
        return
    raise AssertionError(msg)
