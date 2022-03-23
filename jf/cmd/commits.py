#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from dsapy import app

from jf import git


@app.main()
def commits(flags, **kwargs):
    '''List commits (debug).

    Commits are listed as repr of internal commit objects.
    '''
    gc = git.Cache()
    for c in gc.commits.values():
        print(c)


def _run():
    app.start()


if __name__ == '__main__':
    _run()
