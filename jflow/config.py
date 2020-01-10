#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-


VERSION=1


TEMPLATE_KEY_PREFIX = 'jflow.template'

KEY_VERSION = 'version'
KEY_FROM = 'from'
KEY_UPSTREAM = 'upstream'
KEY_PUBLIC = 'public'
KEY_MERGE_TO = 'merge-to'

# Template-only keys
KEY_PUBLIC_PREFIX = 'public-prefix'
KEY_PUBLIC_SUFFIX = 'public-suffix'


def make_key(*items):
    return '.'.join(items)


def branch_key_base(b):
    return make_key('branch', b, 'jflow')


def branch_key_version(b):
    return make_key(branch_key_base(b), KEY_VERSION)


def branch_key_from(b):
    return make_key(branch_key_base(b), KEY_FROM)


def branch_key_upstream(b):
    return make_key(branch_key_base(b), KEY_UPSTREAM)


def branch_key_public(b):
    return make_key(branch_key_base(b), KEY_PUBLIC)


def branch_key_merge_to(b):
    return make_key(branch_key_base(b), KEY_MERGE_TO)
