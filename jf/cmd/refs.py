#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

from dsapy import app

from jf import git


@app.main()
def refs(flags, **kwargs):
    '''List references.'''
    gc = git.Cache()

    # for n, ref in gc.refs.items():
    #     print(f'{n} -> {ref!r}')

    for ref in gc.refs_list:
        print(f'{ref!r}')


@app.main(name='refs-abbrevs')
def refs_abbrevs(**kwargs):
    '''List reference abbreviations.'''
    gc = git.Cache()

    for abbrev, refs in gc.refs_abbrevs.items():
        print('{} -> {}'.format(
            abbrev,
            ', '.join(r.name for r in refs),
        ))


class Abbrevs(app.Command):
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
