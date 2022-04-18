#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Update green-develop."""

import logging

from jf import command
from jf import git
from jf import repo
from jf.cmd import root


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


@root.group.command()
def sync():
    '''Synchronize from remote.'''

    git.check_workdir_is_clean()

    with git.detach_head():
        command.run(['git', 'fetch', '--all', '--prune'])

        gc = repo.Cache()
        for b in gc.branches.values():
            if not b.sync:
                continue
            upstream = b.upstream_resolved
            if not upstream:
                continue
            if gc.is_merged_into(upstream.sha, b.ref.sha):
                continue
            command.run(['git', 'branch', '--force', '--no-track', b.name, upstream.name])
