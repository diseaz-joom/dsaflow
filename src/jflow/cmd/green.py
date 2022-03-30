#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Update green-develop."""

from dsapy import app
from dsapy import flag

from jflow import git
from jflow import green


class Error(Exception):
    '''Base for errors in the module.'''


class Green(green.Mixin, git.Git, app.Command):
    '''Update green-develop.'''
    name='green'

    def main(self):
        self.git_check_workdir_is_clean()
        self.green()


if __name__ == '__main__':
    app.start()
