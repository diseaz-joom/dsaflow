#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Jenkins utils."""

import contextlib
import functools
import logging
import os.path
import pathlib
import urllib.parse as up

import requests


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base class for errors in the module.'''


PREFIX = 'https://api-jenkins.joomdev.net/job/api/job/api-tests/job/'
API_SUFFIX = 'api/json/'
DEFAULT_CRED_PATH = os.path.expanduser('~/.secret/jenkins.cred')


def api_url(u):
    return up.urljoin(u, API_SUFFIX)


def quote(bn):
    bn = up.quote(bn, safe='')
    return up.quote(bn, safe='')


def branch_url(branch, api=False):
    r = '{}{}/'.format(
        PREFIX,
        quote(branch),
    )
    if api:
        r = api_url(r)
    return r


class Mixin:
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--jenkins-auth',
            default=DEFAULT_CRED_PATH,
            help='Path to a file with Jenkins credentials in the form USER:PASSWORD',
        )

    @functools.cached_property
    def jenkins_auth(self):
        user, _, password = pathlib.Path(self.flags.jenkins_auth).read_text().rstrip().partition(':')
        return (user, password)

    @contextlib.contextmanager
    def jenkins_session(self):
        with requests.Session() as ses:
            ses.auth = self.jenkins_auth
            yield ses
