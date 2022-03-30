#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-


VERSION=1


TEMPLATE_KEY_PREFIX = 'jflow.template'
SEPARATOR_KEY = '.'

KEY_VERSION = 'version'
KEY_FORK = 'fork'
KEY_UPSTREAM = 'upstream'
KEY_PUBLIC = 'public'
KEY_DEBUG = 'debug'
KEY_REMOTE = 'remote'
KEY_MERGE_TO = 'merge-to'
KEY_EXTRA = 'extra'

# Template-only keys
KEY_PUBLIC_PREFIX = 'public-prefix'
KEY_PUBLIC_SUFFIX = 'public-suffix'
KEY_DEBUG_PREFIX = 'debug-prefix'
KEY_DEBUG_SUFFIX = 'debug-suffix'
KEY_REMOTE_PREFIX = 'remote-prefix'
KEY_REMOTE_SUFFIX = 'remote-suffix'

DEFAULT_DEBUG_PREFIX = 'feature/'
DEFAULT_DEBUG_SUFFIX = '.debug'
STGIT_SUFFIX = '.stgit'


def make_key(*items):
    return SEPARATOR_KEY.join(items)


def make_prefix(*items):
    return make_key(*items) + SEPARATOR_KEY


def make_suffix(*items):
    return SEPARATOR_KEY + make_key(*items)


def branch_key_base(b):
    return make_key('branch', b, 'jflow')


def branch_key_version(b):
    return make_key(branch_key_base(b), KEY_VERSION)


def branch_key_fork(b):
    return make_key(branch_key_base(b), KEY_FORK)


def branch_key_upstream(b):
    return make_key(branch_key_base(b), KEY_UPSTREAM)


def branch_key_public(b):
    return make_key(branch_key_base(b), KEY_PUBLIC)


def branch_key_debug(b):
    return make_key(branch_key_base(b), KEY_DEBUG)


def branch_key_debug_prefix(b):
    return make_key(branch_key_base(b), KEY_DEBUG_PREFIX)


def branch_key_debug_suffix(b):
    return make_key(branch_key_base(b), KEY_DEBUG_SUFFIX)


def branch_key_remote(b):
    return make_key(branch_key_base(b), KEY_REMOTE)


def branch_key_extra(b):
    return make_key(branch_key_base(b), KEY_EXTRA)


def branch_key_merge_to(b):
    return make_key(branch_key_base(b), KEY_MERGE_TO)


def branch_key_stgit_version(b):
    return make_key('branch', b, 'stgit', 'stackformatversion')


def branch_key_description(b):
    return make_key('branch', b, 'description')


def branch_stgit_name(b):
    return b + STGIT_SUFFIX


def remote_key_url(r):
    return make_key('remote', r, 'url')
