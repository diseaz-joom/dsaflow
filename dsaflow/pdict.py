#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-


class PrefixView(object):
    def __init__(self, dct, prefix='', delim='.'):
        self.dct = dct
        self.prefix = prefix
        self.delim = delim

    def sub_view(self, name):
        return PrefixView(
            self.dct,
            prefix=self.build_key(name),
            delim=self.delim,
        )

    def build_key(self, name):
        return safe_join([self.prefix, name], self.delim)

    def strip_prefix(self, name):
        if not self.prefix:
            return name
        if name.startswith(self.prefix):
            name = name[len(self.prefix):]
        if name.startswith(self.delim):
            name = name[len(self.delim):]
        return name

    def __getitem__(self, name):
        return self.dct[self.build_key(name)]

    def __contains__(self, name):
        return self.build_key(name) in self.dct

    def __iter__(self):
        return self.keys()

    def __len__(self):
        return len(list(self.keys()))

    def __bool__(self):
        for k in self.keys():
            return True
        return False

    def get(self, name, default=None):
        return self.dct.get(self.build_key(name), default)

    def get_path(self, path, default=None):
        return self.get(safe_join(path), default)

    def keys(self):
        return (
            self.strip_prefix(k)
            for k in self.dct
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

    def items(self):
        return (
            (self.strip_prefix(k), v)
            for k, v in self.dct.items()
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

    def values(self):
        return (
            v
            for k, v in self.dct.items()
            if k == self.prefix or (not self.prefix) or k.startswith(self.prefix + self.delim)
        )

def safe_join(ss, delim='.'):
    stripped = [(s or '').strip(delim) for s in ss]
    return delim.join(s for s in stripped if s)
