#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Publish a branch."""

import logging
import re

from dsapy import app

import jflow
from jflow import config
from jflow import git
from jflow import run
from jflow import struct


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''

    @classmethod
    def new(cls, fmt, *args):
        return cls(fmt % tuple(args))


class ToolsMixin(git.Git, run.Cmd):
    def public_branch(self, branch=None):
        branch = branch or self.git_current_ref(short=True)
        return self.git_config_get(config.branch_key_public(branch))

    def publish_local(self, current_branch, public_branch, force_new=False):
        if current_branch == public_branch:
            return
        if force_new:
            self.cmd_action(['stg', 'branch', '--delete', '--force', public_branch])
        self.cmd_action(['stg', 'publish', public_branch])


class ParamsMixin(ToolsMixin):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--debug',
            action='store_true',
            help='Alternative public branch for debugging without spamming PR',
        )

    def params(self, current_branch=None, local=False, pr=False, expand=True, need_url=False):
        p = struct.Struct(
            debug=self.flags.debug,
        )

        p.current_branch = current_branch or self.git_current_ref(short=True)

        if p.debug:
            p.public_branch_name = p.current_branch
        else:
            p.public_branch_name = self.public_branch(p.current_branch)

        if local:
            return p

        # TODO(diseaz): take origin of the upstream branch upstream.
        p.remote_name = 'origin'
        if p.debug:
            p.remote_branch_name = self.git_config_get(config.branch_key_debug(p.current_branch))
        else:
            p.remote_branch_name = self.git_config_get_default(config.branch_key_remote(p.current_branch), p.current_branch)

        if (not pr or p.debug) and not need_url:
            return p

        p.upstream_branch_name = self.git_config_get(config.branch_key_upstream(p.current_branch))
        p.remote_url = self.git_config_get(config.remote_key_url(p.remote_name))
        if not p.remote_url:
            raise Error.new('No URL found for %r', p.remote_name)
        url_m = self.REMOTE_RE.match(p.remote_url)
        if url_m is None:
            raise Error.new('Remote URL %r does not match any known pattern', p.remote_url)
        query = '?expand=1' if expand else ''
        p.pr_url = 'https://github.com/{repo}/compare/{upstream}...{remote}{query}'.format(
            repo=url_m.group('repo'),
            upstream=p.upstream_branch_name,
            remote=p.remote_branch_name,
            query=query,
        )
        return p
