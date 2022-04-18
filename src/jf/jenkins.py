#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Jenkins utils."""

import typing as t

import contextlib
import functools
import logging
import os.path
import pathlib
import urllib.parse as up

import click
import requests


_logger = logging.getLogger(__name__)


F = t.TypeVar("F", bound=t.Callable[..., t.Any])
FC = t.TypeVar("FC", bound=t.Union[t.Callable[..., t.Any], click.Command])


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


def options(f: F) -> F:
    return (
        click.option('--jenkins-auth',
                     help='Path to a file with Jenkins credentials in the form USER:PASSWORD')
        (f)
    )


class Cache:
    def __init__(self, ctx: click.Context):
        self.ctx = ctx

    @functools.cached_property
    def auth(self):
        user, _, password = pathlib.Path(self.ctx.params['jenkins_auth']).read_text().rstrip().partition(':')
        return (user, password)

    @contextlib.contextmanager
    def session(self):
        with requests.Session() as ses:
            ses.auth = self.auth
            yield ses
