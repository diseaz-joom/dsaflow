#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Update tested branch."""

from typing import *

import json
import logging

import requests

from dsapy import app

from jf import command
from jf import git
from jf import jenkins


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


class Mixin(jenkins.Mixin):
    def green_all(self, gc: git.Cache) -> None:
        for branch_name in gc.cfg.jf.default_green.as_list:
            self.green(gc, branch_name)

    def green(self, gc: git.Cache, branch: git.Branch) -> None:
        green_branch_name = branch.tested_branch_name
        if not green_branch_name:
            raise Error('No name for "tested" branch')

        green_ref_name = git.RefName.for_branch(git._REMOTE_LOCAL, green_branch_name)
        green_ref = gc.refs.get(green_ref_name, None)
        green_upstream_ref_name = git.RefName.for_branch(git._REMOTE_ORIGIN, green_branch_name)
        green_upstream_ref = gc.refs.get(green_upstream_ref_name, None)

        branch_ref = branch.ref
        branch_ref_name = branch.ref.name

        if branch_ref_name == green_upstream_ref_name:
            _logger.debug(f'Green: {green_upstream_ref_name!r} == {branch_ref_name!r}')
            return

        green_ref = self.green_sync(gc, green_branch_name)
        green_sha = green_ref.sha if green_ref else None

        with self.jenkins_session() as ses:
            branch_status_r = ses.get(jenkins.branch_url(branch.name, api=True))
            branch_status_r.raise_for_status()
            branch_status = branch_status_r.json()
            for n in ('lastCompletedBuild', 'lastSuccessfulBuild', 'lastStableBuild'):
                _logger.info('%s: %r -> %r', n, branch_status[n]['number'], branch_status[n]['url'])

            last_successful_build_url = jenkins.api_url(branch_status['lastSuccessfulBuild']['url'])
            last_successful_build_r = ses.get(last_successful_build_url)
            last_successful_build_r.raise_for_status()
            last_successful_build = last_successful_build_r.json()

            last_success_action = None
            for action in last_successful_build['actions']:
                builds = action.get('buildsByBranchName')
                if not builds:
                    continue
                develop_build = builds.get(branch.name)
                if not develop_build:
                    continue
                last_success_action = develop_build
                break

            if not last_success_action:
                raise Error('Last successful build not found')

            last_success_sha = last_success_action['revision']['SHA1']

            _logger.info('lastSuccessfulBuildSHA = %r', last_success_sha)

            new_green_sha = last_success_sha

            if new_green_sha not in gc.commits:
                raise Error('Last tested commit not in repo. Run `jf sync`.')

            # Do not move back
            if green_sha and (new_green_sha in gc.commits) and gc.is_merged_into(new_green_sha, green_sha):
                return

            command.run(['git', 'branch', '--no-track', '--force', green_branch_name, new_green_sha])
            if green_upstream_ref:
                command.run([
                    'git', 'branch',
                    '--set-upstream-to={}'.format(green_upstream_ref.name),
                    green_branch_name,
                ])

    def green_sync(self, gc: git.Cache, branch_name: str, ref: git.Ref = None) -> Optional[git.Ref]:
        upstream_ref_name = git.RefName.for_branch(git._REMOTE_ORIGIN, branch_name)
        upstream_ref = gc.refs.get(upstream_ref_name, None)
        if not upstream_ref:
            return ref

        if not ref:
            ref_name = git.RefName.for_branch(git._REMOTE_LOCAL, branch_name)
            ref = gc.refs.get(ref_name, None)
        else:
            ref_name = ref.name

        if not ref:
            command.run(['git', 'branch', '--force', branch_name, upstream_ref.name])
            gc.cfg.branch(branch_name).jf.hidden.set('true')
            return git.Ref(ref_name, upstream_ref.sha)

        if gc.is_merged_into(upstream_ref.sha, ref.sha):
            return ref

        command.run(['git', 'branch', '--force', branch_name, upstream_ref.name])
        return git.Ref(ref_name, upstream_ref.sha)
