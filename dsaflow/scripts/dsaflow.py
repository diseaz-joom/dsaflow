#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Program description."""

import locale
import logging
import subprocess

from dsapy import app
from dsapy import flag


_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


def run(args, check=True, stdout=subprocess.PIPE, stderr=None):
    _logger.info('Run: %r', args)
    return subprocess.run(args, encoding=_encoding, stdout=stdout, stderr=stderr, check=check, universal_newlines=True)


class GitTool(object):
    def git_rev_name(self):
        try:
            p = run(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], stderr=subprocess.DEVNULL)
            return p.stdout
        except subprocess.CalledProcessError:
            pass
        p = run(['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.DEVNULL)
        return p.stdout


class GitRevName(GitTool, app.Command):
    '''Name of the current git revision.'''
    name='git-rev-name'

    def main(self):
        print(self.git_rev_name())


def run():
    app.start()


if __name__ == '__main__':
    run()
