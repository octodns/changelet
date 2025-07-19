#
#
#

from os import makedirs
from os.path import isdir, join
from subprocess import run
from uuid import uuid4


class Create:
    name = 'create'
    description = 'Creates a new changelog entry.'

    def configure(self, parser):
        parser.add_argument(
            '-t',
            '--type',
            choices=('none', 'patch', 'minor', 'major'),
            required=True,
            help='''The scope of the change.

* patch - This is a bug fix
* minor - This adds new functionality or makes changes in a fully backwards
          compatible way
* major - This includes substantial new functionality and/or changes that break
          compatibility and may require careful migration
* none - This change does not need to be mentioned in the changelog

See https://semver.org/ for more info''',
        )
        parser.add_argument(
            '-p',
            '--pr',
            type=int,
            help='Manually override the PR number for the change, maintainer use only.',
        )
        parser.add_argument(
            '-a',
            '--add',
            action='store_true',
            default=False,
            help='`git add` the newly created changelog entry',
        )
        parser.add_argument(
            'description',
            metavar='change-description',
            nargs='+',
            help='''A short description of the changes in this PR, suitable as an entry in
CHANGELOG.md. Should be a single line. Can option include simple markdown formatting
and links.''',
        )

    def run(self, args, directory='.'):
        directory = join(directory, '.changelog')
        if not isdir(directory):
            makedirs(directory)
        filepath = join(directory, f'{uuid4().hex}.md')
        with open(filepath, 'w') as fh:
            fh.write('---\ntype: ')
            fh.write(args.type)
            if args.pr:
                fh.write('\npr: ')
                fh.write(str(args.pr))
            fh.write('\n---\n')
            fh.write(' '.join(args.md))

        if args.add:
            run(['git', 'add', filepath])
            print(
                f'Created {filepath}, it has been staged and should be committed to your branch.'
            )
        else:
            print(
                f'Created {filepath}, it can be further edited and should be committed to your branch.'
            )

        return filepath
