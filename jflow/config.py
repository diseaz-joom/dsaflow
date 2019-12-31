#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-


VERSION=1


def make_key(*items):
    return '.'.join(items)


def branch_key_base(b):
    return make_key('branch', b, 'jflow')


def branch_key_version(b):
    return make_key(branch_key_base(b), 'version')


def branch_key_from(b):
    return make_key(branch_key_base(b), 'from')


def branch_key_upstream(b):
    return make_key(branch_key_base(b), 'upstream')


def branch_key_public(b):
    return make_key(branch_key_base(b), 'public')


def branch_key_merge_to(b):
    return make_key(branch_key_base(b), 'merge-to')
