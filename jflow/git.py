#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import re

import jflow
from jflow import run


class Git(run.Cmd):
    def git_config_set(self, key, value):
        self.cmd_action(['git', 'config', '--local', '--replace-all', str(key), str(value)])

    def git_config_add(self, key, value):
        self.cmd_action(['git', 'config', '--local', '--add', str(key), str(value)])

    def git_config_set_multi(self, key, values):
        if not values:
            return
        self.git_config_set(key, values[0])
        for value in values[1:]:
            self.git_config_add(key, value)

    def git_config_get(self, key):
        for value in self.cmd_output(['git', 'config', '--get', str(key)]):
            # Only return first value
            return value

    def git_config_get_multi(self, key):
        return self.cmd_output(['git', 'config', '--get-all', str(key)])

    def git_config_get_regex(self, prefix, suffix):
        regex_items = []
        if prefix is not None:
            regex_items.append('^' + re.escape(prefix))
        regex_items.append('(.*)')
        if suffix is not None:
            regex_items.append(re.escape(suffix) + '$')
        regex = ''.join(regex_items)
        r = re.compile(regex)
        for line in self.cmd_output(['git', 'config', '--get-regex', str(regex)]):
            name, value = line.split(' ', 1)
            m = r.match(name)
            if not m:
                continue
            yield Value(name, value, key=m.group(1))


class Value(object):
    def __init__(self, name, value, key=None):
        self.name = name
        self.value = value
        self._key = key

    def key(self):
        if self._key is None:
            return self.name
        return self._key

    def __repr__(self):
        return 'Value({!r}, {!r}, {!r})'.format(
            self.name, self.value, self._key,
        )
