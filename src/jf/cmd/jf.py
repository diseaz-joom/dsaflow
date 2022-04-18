#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jf.cmd.root
import jf.cmd.debug

import jf.cmd.config
import jf.cmd.delete
import jf.cmd.green
import jf.cmd.jenkins
import jf.cmd.list
import jf.cmd.publish
import jf.cmd.rebase
import jf.cmd.start
import jf.cmd.sync


(
    jf.cmd.root
    and jf.cmd.debug

    and jf.cmd.config
    and jf.cmd.delete
    and jf.cmd.green
    and jf.cmd.jenkins
    and jf.cmd.list
    and jf.cmd.publish
    and jf.cmd.rebase
    and jf.cmd.start
    and jf.cmd.sync
)


def run():
    jf.cmd.root.group(auto_envvar_prefix='JF')


if __name__ == '__main__':
    run()
