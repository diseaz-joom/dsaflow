#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jf.cmd.config
import jf.cmd.delete
import jf.cmd.jenkins
import jf.cmd.list
import jf.cmd.publish
import jf.cmd.rebase
import jf.cmd.start
import jf.cmd.sync

import jf.cmd.debug

from dsapy import app


(
    jf.cmd.config
    and jf.cmd.delete
    and jf.cmd.jenkins
    and jf.cmd.list
    and jf.cmd.publish
    and jf.cmd.rebase
    and jf.cmd.start
    and jf.cmd.sync

    and jf.cmd.debug
)


def run():
    app.start()


if __name__ == '__main__':
    run()
