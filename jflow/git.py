#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import os
import re
import subprocess

import jflow
from jflow import run


class Error(Exception):
    '''Base class for errors in the module.'''


class Git(run.Cmd):
    def git_config_list_names(self):
        return self.cmd_output(['git', 'config', '--name-only', '--list'])

    def git_config_values(self):
        for line in self.cmd_output(['git', 'config', '--list']):
            name, value = line.split('=', 1)
            yield name, value

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

    def git_config_get_default(self, key, default=None):
        try:
            return self.git_config_get(key)
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                return default
            raise

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

    def _git_current_ref(self, symbolic=True, short=False):
        cmd = ['git', 'rev-parse']
        if symbolic:
            cmd.append('--symbolic-full-name')
        if short:
            cmd.append('--abbrev-ref' if symbolic else '--short')
        cmd.append('HEAD')
        refs = self.cmd_output(cmd)
        if len(refs) != 1:
            raise Error('Unexpected git output: %r', refs)
        return refs[0]

    def git_current_ref(self, short=False):
        ref = self._git_current_ref(symbolic=True, short=short)
        if ref != 'HEAD':
            return ref
        return self._git_current_ref(symbolic=False, short=short)

    def git_workdir_is_clean(self):
        return not self.cmd_output(['git', 'status', '--porcelain', '--untracked-files=no'])

    def git_check_workdir_is_clean(self):
        if not self.git_workdir_is_clean():
            raise Error('Workdir is not clean')

    def git_branch_exists(self, b):
        _, ret = self.cmd_output_ret(['git', 'rev-parse', '--verify', b], check=False)
        return ret == os.EX_OK


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
