import sys

import pygit2
import click
from slugify import slugify

from .utils import taskstatus


class SlugBranchGetter(object):
    prefix = 'feature/'

    def __init__(self, base_branch, remote_credentials, remote_name='origin'):
        self.base_branch = base_branch
        self.remote_name = remote_name
        self.remote_credentials = remote_credentials

    def get_base_branch(self, repo):
        return repo.lookup_branch(
            '{}/{}'.format(self.remote_name, self.base_branch),
            pygit2.GIT_BRANCH_REMOTE
        )

    def get_branch_name(self, prefix, issue):
        discriminator = '{}{}_'.format(prefix, issue.key)
        slug = slugify(issue.fields.summary[:30])
        full_name = '{}{}_{}'.format(self.prefix, issue.key, slug)
        return discriminator, full_name

    def get_branch(self, repo, issue, from_remote=False):
        if from_remote:
            branch_type = pygit2.GIT_BRANCH_REMOTE
            prefix = '{}/{}'.format(self.remote_name, self.prefix)
        else:
            branch_type = pygit2.GIT_BRANCH_LOCAL
            prefix = self.prefix

        discriminator, full_name = self.get_branch_name(prefix, issue)

        branches = [b for b in repo.listall_branches(branch_type)
                    if b.startswith(discriminator)]

        if len(branches) > 1:
            click.secho('Multiple matching branches found!',
                        fg='red', bold=True)
            click.echo()
            click.echo('The prefix {} matched the following branches:'
                       .format(discriminator))
            click.echo()
            for b in branches:
                click.echo(' {} {}'.format(click.style('*', fg='red'), b))
            click.echo()
            click.echo('Please remove all but one in order to continue.')
            sys.exit(1)
        elif branches:
            branch = repo.lookup_branch(branches[0], branch_type)
            if from_remote:
                branch = repo.create_branch(full_name, branch.get_object())
            elif branch.branch_name != full_name:
                # We only need to rename if we're working on an already
                # existing local branch
                branch.rename(full_name)
                branch = repo.lookup_branch(full_name)
            return branch

    def __call__(self, repo, issue, create=True):
        branch = self.get_branch(repo, issue)

        if not branch:
            # No local branches found, fetch remote
            with taskstatus('Fetching from "{}"', self.remote_name) as ts:
                remote = repo.lookup_remote(self.remote_name)
                if not remote:
                    ts.abort('Remote "{}" not found', self.remote_name)

                remote.credentials = self.remote_credentials
                remote.fetch()
                ts.ok('Fetched latest changes from "{}"', self.remote_name)

            # Check remote branches
            with taskstatus('Creating working branch') as ts:
                branch = self.get_branch(repo, issue, from_remote=True)

                # Create off origin base branch
                if branch:
                    ts.ok('Created new working branch based on existing '
                          'remote branch')
                elif create:
                    _, full_name = self.get_branch_name(self.prefix, issue)

                    base = self.get_base_branch(repo)
                    if not base:
                        ts.abort('Base branch "{}" not found on remote "{}"',
                                 self.base_branch, self.remote_name)
                    branch = repo.create_branch(full_name, base.get_object())
                    ts.ok('Created new working branch')

        return branch


class Repository(pygit2.Repository):
    def lookup_remote(self, name):
        for remote in self.remotes:
            if remote.name == name:
                return remote
