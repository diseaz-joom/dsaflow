#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jf.cmd.commits
import jf.cmd.config
import jf.cmd.list
import jf.cmd.rebase
import jf.cmd.refs
import jf.cmd.sync

from dsapy import app


def run():
    app.start()


if __name__ == '__main__':
    run()
