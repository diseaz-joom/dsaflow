#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jf.cmd.commits
import jf.cmd.config
import jf.cmd.debug
import jf.cmd.delete
import jf.cmd.jenkins
import jf.cmd.list
import jf.cmd.publish
import jf.cmd.rebase
import jf.cmd.refs
import jf.cmd.start
import jf.cmd.sync

from dsapy import app


(
    jf.cmd.commits
    and jf.cmd.config
    and jf.cmd.debug
    and jf.cmd.delete
    and jf.cmd.jenkins
    and jf.cmd.list
    and jf.cmd.publish
    and jf.cmd.rebase
    and jf.cmd.refs
    and jf.cmd.start
    and jf.cmd.sync
)


def run():
    app.start()


if __name__ == '__main__':
    run()
