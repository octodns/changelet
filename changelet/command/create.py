#
#
#

from os.path import join
from sys import exit as sys_exit
from sys import stderr
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
            required=False,
            default=None,
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
            '--continue',
            dest='continue_',
            action='store_true',
            default=False,
            help='Continue a previously failed commit attempt',
        )
        parser.add_argument(
            'description',
            metavar='change-description',
            nargs='*',
            default=None,
            help='''A short description of the changes in this PR, suitable as an entry in
CHANGELOG.md. Should be a single line. Can option include simple markdown formatting
and links.''',
        )

    def run(self, args, config):
        if args.continue_:
            filename = config.provider.staged_changelog_entry(config.directory)
            if filename is None:
                print(
                    'No staged changelog entry found to continue.', file=stderr
                )
                return sys_exit(1)

            entry = Entry.load_file(filename)
            description = entry.description

            if not config.provider.has_staged(exclude=filename):
                description = f'{config.commit_prefix}{description}'
            config.provider.commit(description)
            print(
                f'Created {entry.filename}, it has been committed'
                ' along with staged changes.'
            )
            return entry

        if args.commit:
            staged = config.provider.staged_changelog_entry(config.directory)
            if staged:
                print(
                    f'A changelog entry is already staged'
                    f' ({staged}), likely from a previous'
                    f' failed commit attempt. Please run'
                    f' `changelet create --continue` to'
                    f' re-attempt the commit, or unstage'
                    f' the entry with `git reset HEAD'
                    f' {staged}` and try again.',
                    file=stderr,
                )
                return sys_exit(1)

        if args.type is None:
            print('error: -t/--type is required', file=stderr)
            return sys_exit(1)
        if not args.description:
            print('error: description is required', file=stderr)
            return sys_exit(1)

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
            if args.commit:
                has_other_staged = config.provider.has_staged()
            config.provider.add_file(entry.filename)
            if args.commit:
                if not has_other_staged:
                    # if this is going to be a changelog only commit, prefix it
                    description = f'{config.commit_prefix}{description}'
                config.provider.commit(description)
                print(
                    f'Created {entry.filename}, it has been committed'
                    ' along with staged changes.'
                )
            else:
                print(
                    f'Created {entry.filename}, it has been staged and'
                    ' should be committed to your branch.'
                )
        else:
            print(
                f'Created {entry.filename}, it can be further edited'
                ' and should be committed to your branch.'
            )

        return entry
