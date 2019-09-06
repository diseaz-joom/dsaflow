#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

"""Program description."""

import locale
import logging
import os
import re
import subprocess
import sys

from dsapy import app
from dsapy import flag

from dsaflow import pdict


_logger = logging.getLogger(__name__)
_encoding = locale.getpreferredencoding()


class Error(Exception):
    '''Base class for errors in the module.'''


READ = subprocess.PIPE
DEVNULL = subprocess.DEVNULL


class GitTool(object):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config = None

    def git_rev_name(self):
        p = tool(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], stdout=READ, stderr=DEVNULL, check=False)
        if p.returncode == os.EX_OK:
            return p.stdout.strip()
        p = tool(['git', 'rev-parse', '--short', 'HEAD'], stdout=READ, stderr=DEVNULL, check=False)
        if p.returncode == os.EX_OK:
            return p.stdout.strip()
        raise Error('Failed to find revision name')

    def stg_patch_name(self):
        prefix_current = '>'
        try:
            p = tool(['stg', 'series'], stdout=READ, stderr=DEVNULL)
            for line in p.stdout.split('\n'):
                if line.startswith(prefix_current):
                    return p[len(prefix_current):].strip()
        except subprocess.CalledProcessError:
            pass
        raise Error('Failed to find StGit patch name')

    def is_stg(self, name=None):
        if name is None:
            name = self.git_rev_name()
        for b in self.get_branches():
            if b['branch'] == name:
                return b['stgit']
        return False

    def find_branch(self, name):
        p = tool(['git', 'branch', '-a'], stdout=READ)
        branches=[]
        for line in p.stdout.split('\n'):
            line = strip_prefix('*', line).strip()
            line = line.split(' -> ')[0].strip()
            branch_items = line.split('/')
            if name not in branch_items:
                continue
            idx = branch_items.index(name)
            rest = '/'.join(branch_items[idx+1:])
            branches.append(((-idx, idx-len(branch_items), rest), line))
        branches.sort()
        _logger.debug('Branches found for %r: %r', name, [b[1] for b in branches[::-1]])
        try:
            return branches.pop()[1]
        except IndexError:
            raise Error('Failed to find branch for {!r}'.format(name))

    def fork_branch(self, name, from_branch):
        from_branch = self.find_branch(from_branch)
        tool(['git', 'co', '-b', name, from_branch])
        tool(['stg', 'init'])
        tool(['stg', 'new', '--message=main'])

    def branch_prefix(self, branch):
        name_split = branch.split('/', 1)
        if len(name_split) == 1:
            return ''
        return name_split[0].strip()

    def branch_replace_prefix(self, branch, new_prefix):
        name_split = branch.split('/', 1)
        if len(name_split) == 1:
            name_base = name_split[0]
        else:
            name_base = name_split[1]
        return pdict.safe_join([new_prefix, name_base], delim='/')

    def publish_branch(self, name):
        pass

    def get_constructor(self, name):
        return self.default_branch_constructor

    def get_config(self):
        if self.config is None:
            self.config = self._get_config()
        return self.config

    def get_branch_config(self, branch):
        if branch is None:
            branch = self.git_rev_name()

        prefix = 'branch.{}'.format(branch)
        config = self.get_config()
        return pdict.PrefixView(config, prefix=prefix)

    branch_re = re.compile('^(?P<current>[> ]) (?P<stgit>[s ])(?P<protected>[p ])\t(?P<branch>[^ |]*)[ ]*  \| (?P<description>.*)$', re.M)

    def get_branches(self):
        p = tool(['stg', 'branch', '--list'], stdout=READ)
        for m in self.branch_re.finditer(p.stdout):
            yield {
                'branch': m.group('branch'),
                'current': m.group('current') != ' ',
                'stgit': m.group('stgit') != ' ',
                'protected': m.group('protected') != ' ',
                'description': m.group('description'),
            }

    def branch_exists(self, name):
        p = tool(['git', 'branch', '-a'], stdout=READ)
        for b in p.stdout.split('\n'):
            b = strip_prefix('*', b).strip()
            b = b.split(' -> ')[0].strip()
            if name == b:
                return True
        return False

    def _get_config(self):
        p = tool(['git', 'config', '--list', '--null'], stdout=READ)
        config = {}
        for line in p.stdout.split('\0'):
            if not line:
                continue
            nv = line.split('\n', 1)
            if len(nv) != 2:
                _logger.error('Invalid input: %r', nv)
                continue
            name, value = nv
            config[name] = value
        return config

    def get_config_view(self, prefix=None):
        return pdict.PrefixView(self.get_config(), prefix=prefix)

    def get_prefix_key(self, prefix, key, override=None, default=None):
        if override is not None:
            return override

        config = self.get_config_view(pdict.safe_join(['dsaflow.type', prefix], delim='.'))
        value = config.get(key, None)
        if value is not None:
            return value

        config = self.get_config_view('dsaflow.type._default')
        value = config.get(key, None)
        if value is not None:
            return value

        return default

    def get_branch_key(self, branch, key, override=None, default=None):
        if override is not None:
            return override

        config = self.get_config_view(pdict.safe_join(['dsaflow.branch', branch], delim='.'))
        value = config.get(key, None)
        if value is not None:
            return value

        return self.get_prefix_key(self.branch_prefix(branch), key, override=override, default=default)

    def set_branch_key(self, branch, key, value):
        full_key = pdict.safe_join(['dsaflow.branch', branch, key])
        tool(['git', 'config', '--local', full_key, value])


class SyncMixin(object):
    def sync(self):
        branch = self.git_rev_name()

        tool(['git', 'fetch', '--all', '--prune'])
        tool(['git', 'checkout', '--detach', 'HEAD'])
        tool(['git', 'branch', '--force', 'develop', 'origin/develop'])
        tool(['git', 'branch', '--force', 'master', 'origin/master'])
        tool(['git', 'checkout', branch])


class GitRevName(GitTool, app.Command):
    '''Name of the current git revision.'''
    name='git-rev-name'

    def main(self):
        print(self.git_rev_name())


class StgPatchName(GitTool, app.Command):
    '''Name of the current StGit patch.'''
    name='stg-patch-name'

    def main(self):
        print(self.stg_patch_name())


class IsStg(GitTool, app.Command):
    '''Is StGit initialized for the branch?'''
    name='is-stg'

    def main(self):
        if not self.is_stg():
            sys.exit(1)


class InitFlow(GitTool, app.Command):
    '''Initialize flow configuration.'''
    name='init-flow'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--github',
            help='Github repo page URL (https://github.com/USER/REPO)',
        )

    def clean_prefix(self, prefix):
        config_view = self.get_config_view(prefix=prefix)
        for k in config_view.keys():
            tool(['git', 'config', '--local', '--unset', config_view.build_key(k)])

    def main(self):
        self.clean_prefix('dsaflow.ref')
        tool(['git', 'config', '--local', 'dsaflow.ref.develop', 'develop'])
        tool(['git', 'config', '--local', 'dsaflow.ref.master', 'master'])

        self.clean_prefix('dsaflow.type')
        tool(['git', 'config', '--local', 'dsaflow.type._default.fork-from', 'develop'])
        tool(['git', 'config', '--local', 'dsaflow.type._default.local-suffix', 'local'])

        tool(['git', 'config', '--local', 'dsaflow.type.quick.local-suffix', ''])

        tool(['git', 'config', '--local', 'dsaflow.type.hotfix.fork-from', 'master'])

        tool(['git', 'config', '--local', 'dsaflow.type.relfix.fork-from', 'release'])
        tool(['git', 'config', '--local', 'dsaflow.type.relfix.public-prefix', 'feature'])

        tool(['git', 'config', '--local', 'dsaflow.type.junk.local-suffix', ''])
        tool(['git', 'config', '--local', 'dsaflow.type.junk.public-prefix', 'feature'])

        self.clean_prefix('dsaflow.repo')
        if self.flags.github:
            tool(['git', 'config', '--local', 'dsaflow.repo.github', self.flags.github])


class BranchConfig(GitTool, app.Command):
    '''Print branch config.'''
    name='branch-config'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--branch',
            help='Branch',
        )

    def main(self):
        branch_view = self.get_branch_config(self.flags.branch)
        for name, value in branch_view.items():
            print('{}={}'.format(name, value))


class Branches(GitTool, app.Command):
    '''List branches.'''
    name='branches'

    def main(self):
        for b in self.get_branches():
            print(b)


class Start(SyncMixin, GitTool, app.Command):
    '''Start a new branch.'''
    name='start'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            'branch',
            help='Name of the branch to start',
        )
        parser.add_argument(
            '--fork-from',
            help='Fork branch from this branch',
        )
        parser.add_argument(
            '--local-suffix',
            help='Suffix for local branch',
        )
        parser.add_argument(
            '--public-prefix',
            help='Branch prefix for public branch',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Sync before starting',
        )

    def main(self):
        branch = self.flags.branch
        if not branch:
            raise Error('Empty branch name')

        branch_prefix = self.branch_prefix(branch)
        local_suffix = self.get_prefix_key(branch_prefix, 'local-suffix', override=self.flags.local_suffix, default='')
        public_prefix = self.get_prefix_key(branch_prefix, 'public-prefix', override=self.flags.public_prefix, default=branch_prefix)
        fork_from = self.get_prefix_key(branch_prefix, 'fork-from', override=self.flags.fork_from)

        refs_config = self.get_config_view('dsaflow.refs')
        fork_from = refs_config.get(fork_from, fork_from)
        if not fork_from:
            raise Error('Do not know what branch to fork')

        if self.flags.sync:
            self.sync()

        local_branch = pdict.safe_join([branch, local_suffix])
        self.fork_branch(local_branch, from_branch=fork_from)

        self.set_branch_key(local_branch, 'local-suffix', local_suffix)
        self.set_branch_key(local_branch, 'public-prefix', public_prefix)
        self.set_branch_key(local_branch, 'fork-from', fork_from)


class Publish(GitTool, app.Command):
    '''Publish branch.'''
    name='publish'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--from-scratch',
            action='store_true',
            help='Publish from scratch',
        )
        parser.add_argument(
            '--pr',
            action='store_true',
            help='Create PR',
        )

    def main(self):
        local_branch = self.git_rev_name()

        local_suffix = self.get_branch_key(local_branch, 'local-suffix')
        public_prefix = self.get_branch_key(local_branch, 'public-prefix')
        fork_from = self.get_branch_key(local_branch, 'fork-from')

        refs_config = self.get_config_view('dsaflow.refs')
        fork_from = refs_config.get(fork_from, fork_from)
        if not fork_from:
            raise Error('Do not know what source branch was')

        pub_branch = strip_suffix('.' + local_suffix, local_branch)
        pub_branch = self.branch_replace_prefix(pub_branch, public_prefix)

        if pub_branch != local_branch:
            if self.flags.from_scratch and self.branch_exists(pub_branch):
                tool(['git', 'branch', '--delete', '--force', pub_branch])
            tool(['stg', 'publish', pub_branch])
        tool(['git', 'push', '--force', '--set-upstream', 'origin', '{0}:{0}'.format(pub_branch)])

        config = self.get_config_view('dsaflow.repo')
        repo = config.get('github')
        _logger.debug('Repo: %r', repo)
        if repo and self.flags.pr:
            tool(['xdg-open',
                  '{v[repo]}/compare/{v[fork_from]}...{v[pub_branch]}?expand=1'.format(v=locals()),
            ])


class Sync(SyncMixin, GitTool, app.Command):
    '''Pull changes from upstream.'''
    name='sync'

    def main(self):
        self.sync()


class Rebase(SyncMixin, GitTool, app.Command):
    '''Rebase branch to an updated fork source.'''
    name='rebase'

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--sync',
            action='store_true',
            help='Sync before rebase',
        )

    def main(self):
        if self.flags.sync:
            self.sync()

        local_branch = self.git_rev_name()

        local_suffix = self.get_branch_key(local_branch, 'local-suffix')
        public_prefix = self.get_branch_key(local_branch, 'public-prefix')
        fork_from = self.get_branch_key(local_branch, 'fork-from')

        refs_config = self.get_config_view('dsaflow.refs')
        fork_from = refs_config.get(fork_from, fork_from)
        if not fork_from:
            raise Error('Do not know what source branch was')

        tool(['stg', 'rebase', fork_from])


def tool(args, check=True, stdout=None, stderr=None):
    _logger.debug('Run: %r', args)
    return subprocess.run(args, encoding=_encoding, stdout=stdout, stderr=stderr, check=check, universal_newlines=True)


def strip_prefix(prefix, s):
    if s.startswith(prefix):
        return s[len(prefix):]
    return s


def strip_suffix(suffix, s):
    if s.endswith(suffix):
        return s[:len(s) - len(suffix)]
    return s


def run():
    app.start()


if __name__ == '__main__':
    run()
