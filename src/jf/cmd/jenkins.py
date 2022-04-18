#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Open jenkins build page."""

import click

from jf import command
from jf import git
from jf import jenkins
from jf import repo
from jf.cmd import root


class Error(Exception):
    '''Base class for errors in the module.'''


@root.group.command('jenkins')
@click.option('--debug', is_flag=True, default=False,
              help='Alternative public branch for debugging without spamming PR')
@click.argument('branch', required=False, default=git.current_branch)
def jenkins_cmd(branch: str, debug: bool):
    '''Open jenkins build page.'''
    gc = repo.Cache()

    if not branch:
        raise Error('HEAD is not a branch')
    b = gc.branches[branch]

    build_branch_name = b.debug_branch_name if debug else b.review_branch_name
    url = jenkins.branch_url(build_branch_name)
    command.run(['xdg-open', url])
