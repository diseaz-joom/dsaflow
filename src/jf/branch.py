#!/usr/bin/python3
# -*- mode: python; coding: utf-8 -*-

import functools
import logging
import typing as t

from jf import config
from jf import git


_logger = logging.getLogger(__name__)


class Error(Exception):
    '''Base for errors in the module.'''


class UnsupportedJflowVersionError(Error):
    '''Unsupported Jflow version.'''

    def __init__(self, v):
        return super(f'Unsupported Jflow version: {v}')


class Generic:
    '''Branch is umbrella entity to describe logical branch.

    Logical branch includes several required physical branches.

        - Main branch, referenced by `ref` property is the branch in the local
          repository you directly work with.  It's usually under StGit control.

        - `upstream` is what main branch is logically tracks and eventually will
          be merged into.

        - `fork` is what main branch is physically forked from.  It may be
          different from upstream.  E.g. there may be a branch that follows
          upstream branch and only fast-forwards only if CI tests are passed.
          It's a good idea to put this branch as `fork`.

        - `stgit` branch is a technical branch for StGit.

        - `public` branch is a review-friendly branch in the local repository.
          With some configurations it can be the same as the main branch.
          Usually, for StGit-controlled branches `stg publish` builds public
          branch.

        - `review` is a branch in remote repository for review.  Usually it is a
          public branch pushed into remote repository.

        - `debug` is a branch in remote repository for running CI tests.

        - `ldebug` is a debug branch in the local repository.

        - `tested` branch is what new branches should be forked from by default
          if this branch is upstream.  It's not only for jflow-controlled
          branches.
    '''

    def __init__(self, cfg: config.Root, ref: git.RefName):
        if not ref.branch:
            raise Error(f'Invalid branch ref: {ref}')
        self.ref = ref
        self.cfg_root = cfg
        self.cfg = cfg.branch[self.name]

    def __repr__(self):
        return 'GenericBranch({})'.format(self.ref)

    @property
    def name(self) -> str:
        return self.ref.short

    @property
    def remote(self) -> str:
        return self.cfg.jf.remote.value or self.cfg.jf.remote.value or git.REMOTE_ORIGIN

    @functools.cached_property
    def description(self) -> str:
        return self.cfg.description.value

    @functools.cached_property
    def protected(self) -> bool:
        return self.cfg.jf.protected.value

    @functools.cached_property
    def hidden(self) -> bool:
        return self.cfg.jf.hidden.value

    @property
    def is_jflow(self) -> bool:
        return bool(self.jflow_version)

    @functools.cached_property
    def jflow_version(self) -> int:
        return self.cfg.jf.version.value

    @property
    def is_stgit(self) -> bool:
        return bool(self.cfg.stgit.version.value)

    @functools.cached_property
    def stgit(self) -> t.Optional[git.RefName]:
        if not self.is_stgit:
            return None
        return git.RefName(self.ref + git.STGIT_SUFFIX)

    @functools.cached_property
    def review(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            bn = self.cfg.jf.review.value
            if not bn:
                return None
            return bn.ref(self.remote)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def public(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            bn = self.cfg.jf.lreview.value
            if not bn:
                return None
            return bn.ref(git.REMOTE_LOCAL)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def debug(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            bn = self.cfg.jf.debug.value
            if not bn:
                return None
            return bn.ref(self.remote)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def ldebug(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            return None
        elif self.jflow_version == 1:
            bn = self.cfg.jf.ldebug.value or self.cfg.jf.debug.value
            if not bn:
                return None
            return bn.ref(git.REMOTE_LOCAL)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def upstream(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            if not self.cfg.merge.value:
                return None
            br = git.RefName(self.cfg.merge.value)
            if not br.branch:
                return None
            return br.branch.ref(self.cfg.remote.value)
        elif self.jflow_version == 1:
            return self.cfg.jf.upstream.value.ref(git.REMOTE_LOCAL)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def fork(self) -> t.Optional[git.RefName]:
        if not self.jflow_version:
            return self.upstream
        elif self.jflow_version == 1:
            bn = self.cfg.jf.fork.value
            if not bn:
                return self.upstream
            return bn.ref(git.REMOTE_LOCAL)
        raise UnsupportedJflowVersionError(self.jflow_version)

    @functools.cached_property
    def tested(self) -> t.Optional[git.RefName]:
        bn = self.cfg.jf.tested.value
        if not bn:
            return None
        return bn.ref(git.REMOTE_LOCAL)

    @functools.cached_property
    def sync(self) -> bool:
        if self.is_jflow:
            return False
        if self.cfg.jf.sync.value:
            return True
        if not self.cfg_root.jf.autosync.value:
            return False
        if not (self.upstream and self.upstream.is_remote):
            return False
        return True

    def gen_related_refs(self) -> t.Generator[git.RefName, None, None]:
        if self.public and self.public != self.ref:
            yield self.public
        if self.ldebug and self.ldebug != self.ref:
            yield self.ldebug
        if self.stgit:
            yield self.stgit
