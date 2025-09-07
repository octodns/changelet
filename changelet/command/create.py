#
#
#

from os.path import join
from uuid import uuid4

from changelet.entry import Entry


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
            '-c',
            '--commit',
            action='store_true',
            default=False,
            help='`git commit` add the entry and commit staged changes using the same description',
        )
        parser.add_argument(
            'description',
            metavar='change-description',
            nargs='+',
            help='''A short description of the changes in this PR, suitable as an entry in
CHANGELOG.md. Should be a single line. Can option include simple markdown formatting
and links.''',
        )

    def run(self, args, config):
        filename = join(config.directory, f'{uuid4().hex}.md')
        description = ' '.join(args.description)
        entry = Entry(
            type=args.type,
            description=description,
            pr=args.pr,
            filename=filename,
        )
        entry.save()

        if args.add or args.commit:
            config.provider.add_file(entry.filename)
            if args.commit:
                if not config.provider.has_staged():
                    # if this is going to be a changelog only commit, prefix it
                    description = f'{config.commit_prefix}{description}'
                config.provider.commit(description)
                print(
                    f'Created {entry.filename}, it has been committed along with staged changes.'
                )
            else:
                print(
                    f'Created {entry.filename}, it has been staged and should be committed to your branch.'
                )
        else:
            print(
                f'Created {entry.filename}, it can be further edited and should be committed to your branch.'
            )

        return entry
