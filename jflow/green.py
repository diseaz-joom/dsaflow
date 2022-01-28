#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Update green-develop."""

import contextlib
import json
import logging
import pathlib
import pprint
import re
import sys
import urllib.parse as up

import requests

from dsapy import app

from jflow import config
from jflow import git
from jflow import run


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


JENKINS_PREFIX = 'https://api-jenkins.joomdev.net/job/api/job/api-tests/job/'
JENKINS_API_SUFFIX = 'api/json/'

GREEN_DEVELOP="tested/develop"
GREEN_DEVELOP_UPSTREAM="origin/tested/develop"


def jenkins_api_url(u):
    return up.urljoin(u, JENKINS_API_SUFFIX)


def jenkins_quote(bn):
    bn = up.quote(bn, safe='')
    return up.quote(bn, safe='')


def jenkins_branch_url(branch, api=False):
    r = '{}{}/'.format(
        JENKINS_PREFIX,
        jenkins_quote(branch),
    )
    if api:
        r = jenkins_api_url(r)
    return r


class Mixin(git.Git, run.Cmd):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--jenkins-auth',
            default='~/.secret/jenkins.cred',
            help='Path to a file with Jenkins credentials in the form USER:PASSWORD',
        )

    def jenkins_auth(self):
        user, password = pathlib.Path(self.flags.jenkins_auth).expanduser().read_text().strip().split(':')
        return (user, password)


    @contextlib.contextmanager
    def jenkins_session(self):
        with requests.Session() as ses:
            ses.auth = self.jenkins_auth()
            yield ses


    def green(self):
        with self.jenkins_session() as ses:
            branch_status_r = ses.get(jenkins_branch_url('develop', True))
            branch_status_r.raise_for_status()
            branch_status = branch_status_r.json()
            for n in ('lastCompletedBuild', 'lastSuccessfulBuild', 'lastStableBuild'):  # , 'lastBuild', 'lastFailedBuild', 'lastUnstableBuild', 'lastUnsuccessfulBuild'):
                _logger.info('%s: %r -> %r', n, branch_status[n]['number'], branch_status[n]['url'])

            last_successful_build_url = jenkins_api_url(branch_status['lastSuccessfulBuild']['url'])
            last_successful_build_r = ses.get(last_successful_build_url)
            last_successful_build_r.raise_for_status()
            last_successful_build = last_successful_build_r.json()

            last_success_action = None
            for action in last_successful_build['actions']:
                builds = action.get('buildsByBranchName')
                if not builds:
                    continue
                develop_build = builds.get('develop')
                if not develop_build:
                    continue
                last_success_action = develop_build
                break

            if not last_success_action:
                raise Error('Last successful build not found')

            last_success_sha = last_success_action['revision']['SHA1']

            _logger.info('lastSuccessfulBuildSHA = %r', last_success_sha)

            self.cmd_action(['git', 'branch', '--no-track', '--force', 'tested/develop', last_success_sha])
            self.cmd_action([
                'git', 'branch',
                '--set-upstream-to={}'.format(GREEN_DEVELOP_UPSTREAM),
                GREEN_DEVELOP,
            ])
