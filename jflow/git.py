#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import jflow
from jflow import run


class Git(object):
    pass


def set_config_value(key, value):
    run.action(['git', 'config', '--local', '--replace-all', str(key), str(value)])


def add_config_value(key, value):
    run.action(['git', 'config', '--local', '--add', str(key), str(value)])


def set_config_values(key, values):
    if not values:
        return
    set_config_value(key, values[0])
    for value in values[1:]:
        add_config_value(key, value)


def get_config_value(key):
    for value in run.get_output(['git', 'config', '--get', str(key)]):
        return value


def get_config_values(key):
    return run.get_output(['git', 'config', '--get-all', str(key)])
