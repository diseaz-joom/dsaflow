#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Rebase branch to a fresh tip."""

from typing import Optional, List

import logging
import re
import urllib.parse

import click

from jf import command
from jf import git
from jf import repo
from jf.cmd import root


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


@root.group.command()
@click.option('-m', '--message',
              help='Message to commit current changes before rebase')
@click.option('--debug', is_flag=True, default=False,
              help='Alternative public branch for debugging without spamming PR')
@click.option('--new', is_flag=True, default=False,
              help='Start public branch anew')
@click.option('--local', is_flag=True, default=False,
              help='Only update local public branch')
@click.option('--pr', is_flag=True, default=False,
              help='Create PR')
@click.option('--non-clean', is_flag=True, default=False,
              help='Force action with non clean workdir')
def publish(message: str, debug: bool, new: bool, local: bool, pr: bool, non_clean: bool):
    '''Publish a branch for review.'''

    if not non_clean:
        git.check_workdir_is_clean()

    gc = repo.Cache()

    branch_name = git.current_branch
    if not branch_name:
        raise Error('HEAD is not a branch')
    branch = gc.branches[branch_name]

    if debug:
        publish_func = branch.publish_local_debug
    else:
        publish_func = branch.publish_local_public

    local_ref, remote_ref = publish_func(msg=message, force_new=new)

    if local:
        return
    if not local_ref:
        return

    if not branch.upstream_name:
        raise Error(f'No upstream for branch {branch.name!r}')
    if not remote_ref:
        raise Error('No remote reference calculated')
    if not remote_ref.branch:
        raise Error(f'Failed to extract branch name from ref {remote_ref}')
    remote_branch_ref = git.RefName.for_branch(git.REMOTE_LOCAL, remote_ref.branch)

    command.run([
        'git', 'push', '--force', remote_ref.remote,
        f'{local_ref}:{remote_branch_ref}'])

    if not pr:
        return

    pr_url = _review_url(gc, branch, remote_ref, branch.upstream_name)
    if pr_url:
        command.run(['xdg-open', pr_url])


_GITHUB_REMOTE_RE = re.compile('(?:https://|[-_+a-z0-9]+@)?github\\.com[:/](?P<repo>.*?)(?:\\.git)?$')
_FIX_RE = re.compile('\\[fix:(?P<issue>[^\x5D]+)\\]', re.I)


def _github_review_url(
        remote_url: str,
        branch: git.GenericBranch,
        feature: git.RefName,
        upstream: git.RefName,
) -> Optional[str]:
    github_m = _GITHUB_REMOTE_RE.match(remote_url)
    if not github_m:
        return None

    title = ''
    body = ''

    issues: List[str] = []

    def extract_issue(m):
        issues.append(m.group('issue'))
        return ''

    if branch.description:
        title = _FIX_RE.sub(extract_issue, branch.description).strip()

    if issues:
        body = body + '\n'.join(f'Fixes {issue}' for issue in issues)

    param_dict = {
        'quick_pull': 1,
        'title': title,
        'body': body,
    }
    params = urllib.parse.urlencode({k: v for k, v in param_dict.items() if v})
    if params:
        params = '?' + params

    return (f'https://github.com/'
            f'{github_m["repo"]}/'
            f'compare/{upstream.branch}...{feature.branch}'
            f'{params}')


def _review_url(
        gc: repo.Cache,
        branch: git.GenericBranch,
        feature: git.RefName,
        upstream: git.RefName,
) -> Optional[str]:
    if not feature.remote:
        return None

    remote_url = gc.cfg.remote[feature.remote].url.value
    if not remote_url:
        return None

    return _github_review_url(remote_url, branch, feature, upstream)
