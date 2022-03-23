#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jf.cmd.branch
import jf.cmd.commits
import jf.cmd.green
import jf.cmd.list
import jf.cmd.rebase
import jf.cmd.refs

from dsapy import app


def run():
    app.start()


if __name__ == '__main__':
    run()
