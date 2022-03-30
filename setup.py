#!/usr/bin/python3

# Workaround as described here: https://github.com/pypa/pip/issues/7953
import site
site.ENABLE_USER_SITE = True

import setuptools

setuptools.setup()
