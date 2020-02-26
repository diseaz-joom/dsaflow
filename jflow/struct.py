#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

class Object(object):
    '''Just an empty object.'''


class Struct(dict):
    '''An object to access members both as `[x]` and as `.x`.'''

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__dict__ = self
