#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Useful tools to implement Joom workflow."""

from dsapy import app
from dsapy import flag

import jflow.cmd.start
import jflow.cmd.rebase
import jflow.cmd.resolve


def run():
    app.start()


if __name__ == '__main__':
    run()
