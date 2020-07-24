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


JENKINS_PREFIX = 'https://jenkins.joom.it/view/api-tests/job/backend-api/job/'
JENKINS_API_SUFFIX = 'api/json/'


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

        parser.add_argument(
            '--no-green',
            action='store_true',
            help='Do not update green-develop branch',
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
            ra = ses.get(jenkins_branch_url('develop', True))
            raj = ra.json()
            for n in ('lastBuild', 'lastCompletedBuild', 'lastFailedBuild', 'lastStableBuild', 'lastSuccessfulBuild', 'lastUnstableBuild', 'lastUnsuccessfulBuild'):
                _logger.info('%s: %r -> %r', n, raj[n]['number'], raj[n]['url'])

            last_successful_build_url = jenkins_api_url(raj['lastSuccessfulBuild']['url'])
            rsb = ses.get(last_successful_build_url)
            rsbj = rsb.json()
            json.dump(
                rsbj, sys.stdout,
                ensure_ascii=False,
                indent=4,
                sort_keys=True,
            )

            actions = rsbj['actions']


            # last_build_url = jenkins_api_url(raj['lastBuild']['url'])
            # rb = ses.get(last_build_url)
            # rbj = rb.json()
            # json.dump(
            #     rbj, sys.stdout,
            #     ensure_ascii=False,
            #     indent=4,
            #     sort_keys=True,
            # )
