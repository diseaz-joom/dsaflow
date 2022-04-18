#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import typing as t

import logging

import click

from jf import command


_logger = logging.getLogger(__name__)


F = t.TypeVar("F", bound=t.Callable[..., t.Any])
FC = t.TypeVar("FC", bound=t.Union[t.Callable[..., t.Any], click.Command])


_log_levels = {
    'critical': logging.CRITICAL,
    'fatal': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'warn': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG,
}

_log_datefmt = '%Y-%m-%d %H:%M:%S'

_log_formats = {
    'tiny': '%(message)s',
    'short': '%(asctime)s %(message)s',
    'long': '%(asctime)s %(levelname)s %(name)s@%(lineno)d: %(message)s',
}

_context_settings = {
    'help_option_names': ['-h', '--help'],
}


@click.group(context_settings=_context_settings)
@click.option('--log-level', type=click.Choice(list(_log_levels.keys()), case_sensitive=False), default='info')
@click.option('--log-format', type=click.Choice(list(_log_formats.keys()), case_sensitive=False), default='short')
@command.options
@click.pass_context
def group(ctx: click.Context, log_level: str, log_format: str, **kwargs):
    '''Sample tool.'''

    logging.basicConfig(
        level=_log_levels[log_level],
        datefmt=_log_datefmt,
        format=_log_formats[log_format],
    )

    command.process_options(ctx)


def _param_memo(f, params):
    if isinstance(f, click.Command):
        f.params.extend(params)
    else:
        if not hasattr(f, "__click_params__"):
            f.__click_params__ = []  # type: ignore

        f.__click_params__.extend(params)  # type: ignore


def combine_options(src: click.Command) -> t.Callable[[FC], FC]:
    def decorator(f: F) -> F:
        _param_memo(f, src.params)
        return f
    return decorator
