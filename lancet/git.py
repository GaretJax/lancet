import sys
import click
from slugify import slugify


class SlugBranchGetter(object):
    prefix = 'feature/'

    def __init__(self, base_branch='master'):
        self.base_branch = base_branch

    def __call__(self, repo, issue):
        discriminator = '{}{}'.format(self.prefix, issue.key)
        slug = slugify(issue.fields.summary[:30])
        full_name = '{}_{}'.format(discriminator, slug)

        branches = [b for b in repo.listall_branches()
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
            branch = repo.lookup_branch(branches[0])
            if branch.branch_name != full_name:
                branch.rename(full_name)
                branch = repo.lookup_branch(full_name)
        else:
            base = repo.lookup_branch(self.base_branch)
            if not base:
                click.secho('Base branch not found: "{}", aborting.'
                            .format(self.base_branch), fg='red', bold=True)
                sys.exit(1)
            branch = repo.create_branch(full_name, base.get_object())

        return branch
