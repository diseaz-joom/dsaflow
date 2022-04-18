#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from dsapy import app

from jf import config
from jf import git
from jf import repo


class Error(Exception):
    '''Base for errors in the module.'''


class Info(app.Command):
    '''(debug) display branch info.'''

    name = 'info'

    _BRANCH_PROPS = [
        'name',
        'remote',
        'is_jflow',
        'is_stgit',
        'upstream_name',
        'upstream',
        'fork_name',
        'fork',
        'ldebug_name',
        'ldebug',
        'debug_name',
        'debug',
        'public_name',
        'public',
        'review_name',
        'review',
        'hidden',
        'protected',
        'sync',
        'tested_branch_name',
        'tested',
    ]

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'branch',
            nargs='?',
            default=git.current_branch,
            help='Branch to operate on',
        )

    def main(self):
        gc = repo.Cache()
        b = gc.branches[self.flags.branch]
        print('Branch:')
        for k in self._BRANCH_PROPS:
            kv = getattr(b, k)
            print(f'  {k}: {kv!r}')
        bk = gc.cfg.branch[b.name].jf
        print(f'Jflow config ({bk.path}):')
        for k in config.JfBranchCfg.KEYS:
            kk = getattr(bk, k)
            print(f'  {k}: {kk.value!r}')


@app.main()
def commits(flags, **kwargs):
    '''(debug) list commits.

    Commits are listed as repr of internal commit objects.
    '''
    gc = repo.Cache()
    for c in gc.commits.values():
        print(c)


class Resolve(app.Command):
    '''(debug) resolve shortcut into ref.'''

    name = 'resolve'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'shortcut',
            help='Shortcut to resolve',
        )

    def main(self):
        gc = repo.Cache()
        r = gc.resolve_shortcut(self.flags.shortcut)
        print(f'Resolved: {r!r}')


class Templates(app.Command):
    '''(debug) list templates.'''
    name = 'templates'

    def main(self):
        cfg = config.Root()
        for t in cfg.jf.template.keys:
            print(f'{t!r}')


@app.main()
def refs(flags, **kwargs):
    '''(debug) list references.'''
    gc = repo.Cache()

    for ref in gc.refs_list:
        print(f'{ref!r}')


@app.main(name='refs-abbrevs')
def refs_abbrevs(**kwargs):
    '''(debug) list reference abbreviations.'''
    gc = repo.Cache()

    for abbrev, refs in gc.refs_abbrevs.items():
        print('{} -> {}'.format(
            abbrev,
            ', '.join(r.name for r in refs),
        ))


class Abbrevs(app.Command):
    '''(debug) display abbreviations for the ref.'''

    name = 'abbrevs'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'ref',
            nargs='?',
            default=git.current_ref,
            help='Reference name to generate abbrevs for',
        )

    def main(self):
        for abbr in git.ref_abbrevs(self.flags.ref):
            print(f'{abbr!r}')


def _run():
    app.start()


if __name__ == '__main__':
    _run()
