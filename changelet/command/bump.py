#
#
#

from datetime import datetime
from importlib import import_module
from io import StringIO
from os.path import abspath, basename, join
from sys import exit, path, stderr

from semver import Version

from changelet.entry import Entry, EntryType


def _get_current_version(module_name, directory='.'):
    # temporarily prepend directory to sys.path so we import from CWD rather
    # than a virtualenv or system install. If the module is in a subdirectory,
    # e.g. lib/the_thing, it'll be on the user to get the correct one in the
    # path
    original_path = path.copy()
    path.insert(0, directory)
    try:
        module = import_module(module_name)
        return Version.parse(module.__version__)
    finally:
        path[:] = original_path


def _get_new_version(current_version, entries):
    try:
        bump_type = entries[0].type
    except IndexError:
        return None
    if bump_type == EntryType.MAJOR:
        return current_version.bump_major()
    elif bump_type == EntryType.MINOR:
        return current_version.bump_minor()
    elif bump_type == EntryType.PATCH:
        return current_version.bump_patch()
    return None


def version(value):
    return Version.parse(value)


class Bump:
    name = 'bump'
    description = (
        'Builds a changelog update and calculates a new version number.'
    )

    def configure(self, parser):
        parser.add_argument(
            '--version',
            type=version,
            required=False,
            help='Use the supplied version number for the bump',
        )
        parser.add_argument(
            '--make-changes',
            action='store_true',
            help='Write changelog update and bump version number',
        )
        parser.add_argument(
            '--pr',
            action='store_true',
            help='Create a pull request with the version bump',
        )
        parser.add_argument(
            '--ignore-local-changes',
            action='store_true',
            help='Skip checking for local changes when using --pr',
        )
        parser.add_argument(
            'title', nargs='*', help='A short title/quip for the release title'
        )

    def exit(self, code):
        exit(code)

    def run(self, args, config, root='.'):
        # If --pr is specified, validate git state and handle PR workflow
        if args.pr:
            # Check we're on main branch
            current_branch = config.provider.current_branch()
            base_branch = config.provider.base_branch
            if current_branch != base_branch:
                print(
                    f'Error: Must be on {base_branch} branch, currently on {current_branch}',
                    file=stderr,
                )
                return self.exit(1)

            # Check for unstaged changes (unless --ignore-local-changes is set)
            if not args.ignore_local_changes:
                if config.provider.has_local_changes():
                    print(
                        'Error: Unstaged changes detected. Please commit or stash them.',
                        file=stderr,
                    )
                    return self.exit(1)

            # Pull latest changes
            config.provider.pull()

        buf = StringIO()

        module_name = basename(abspath(root)).replace('-', '_')

        buf.write('## ')
        current_version = _get_current_version(module_name)

        entries = sorted(Entry.load_all(config), reverse=True)

        new_version = (
            args.version
            if args.version
            else _get_new_version(current_version, entries)
        )
        if not new_version:
            print('No changelog entries found that would bump, nothing to do')
            return self.exit(1)
        buf.write(str(new_version))
        buf.write(' - ')
        buf.write(datetime.now().strftime('%Y-%m-%d'))
        if args.title:
            buf.write(' - ')
            buf.write(' '.join(args.title))
        buf.write('\n')

        current_type = None
        for entry in entries:
            type = entry.type
            if type == EntryType.NONE:
                # these aren't included in the listing
                continue
            if type != current_type:
                buf.write('\n')
                buf.write(type.value.capitalize())
                buf.write(':\n')
                current_type = type
            buf.write(entry.markdown)

            buf.write('\n')

        buf.write('\n')

        buf = buf.getvalue()
        if not args.make_changes and not args.pr:
            print(f'New version number {new_version}\n')
            print(buf)
            self.exit(0)
        else:
            # If --pr is specified, create branch and make changes
            branch_name = f'rel-{new_version.major}-{new_version.minor}-{new_version.patch}'
            if args.pr:
                config.provider.create_branch(branch_name)

            changelog = join(root, 'CHANGELOG.md')
            with open(changelog) as fh:
                existing = fh.read()

            with open(changelog, 'w') as fh:
                fh.write(buf)
                fh.write(existing)

            init = join(root, module_name, '__init__.py')
            with open(init) as fh:
                existing = fh.read()

            with open(init, 'w') as fh:
                fh.write(
                    existing.replace(str(current_version), str(new_version))
                )

            for entry in entries:
                entry.remove()

            # If --pr is specified, stage, commit, push, and create PR
            if args.pr:
                # Stage the specific files we modified
                config.provider.add_file(changelog)
                config.provider.add_file(init)
                for entry in entries:
                    if entry.filename:
                        config.provider.add_file(entry.filename)

                # Commit changes
                commit_message = f'Version {new_version.major}.{new_version.minor}.{new_version.patch} bump & changelog update'
                config.provider.commit(commit_message)

                # Push to origin
                config.provider.push_branch(branch_name)

                # Create PR
                url = config.provider.create_pr(commit_message, buf)
                print(url)

        return new_version, buf
