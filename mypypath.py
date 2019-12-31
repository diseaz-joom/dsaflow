#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import os
import sys

home = os.path.expanduser('~')
paths = [p for p in sys.path if p.startswith(home) and 'site-packages' not in p]
print('export MYPYPATH={}'.format(':'.join(paths)))
