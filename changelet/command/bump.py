#
#
#

from datetime import datetime
from importlib import import_module
from io import StringIO
from os.path import abspath, basename, join
from subprocess import run
from sys import exit, path, stderr

from semver import Version

from changelet.entry import Entry


def _get_current_version(module_name, directory='.'):
    # make sure that our current directory is in the python path so that we
    # prefer the version accessible in our CWD. If the module is in a
    # subdirectory, e.g. lib/the_thing, it'll be on the user to get the correct
    # one in the path
    path.insert(0, directory)
    module = import_module(module_name)
    return Version.parse(module.__version__)


def _get_new_version(current_version, entries):
    try:
        bump_type = entries[0].type
    except IndexError:
        return None
    if bump_type == 'major':
        return current_version.bump_major()
    elif bump_type == 'minor':
        return current_version.bump_minor()
    elif bump_type == 'patch':
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
            'title', nargs='*', help='A short title/quip for the release title'
        )

    def exit(self, code):
        exit(code)

    def run(self, args, config, root='.'):
        # If --pr is specified, validate git state and handle PR workflow
        if args.pr:
            # Check we're on main branch
            result = run(
                ['git', 'branch', '--show-current'],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print('Failed to get current branch', file=stderr)
                return self.exit(1)
            current_branch = result.stdout.strip()
            if current_branch != 'main':
                print(
                    f'Error: Must be on main branch, currently on {current_branch}',
                    file=stderr,
                )
                return self.exit(1)

            # Check for unstaged changes
            result = run(
                ['git', 'status', '--porcelain'], capture_output=True, text=True
            )
            if result.returncode != 0:
                print('Failed to check git status', file=stderr)
                return self.exit(1)
            if result.stdout.strip():
                print(
                    'Error: Unstaged changes detected. Please commit or stash them.',
                    file=stderr,
                )
                return self.exit(1)

            # Pull latest changes
            result = run(['git', 'pull'], capture_output=True, text=True)
            if result.returncode != 0:
                print('Failed to pull latest changes', file=stderr)
                print(result.stderr, file=stderr)
                return self.exit(1)

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
            if type == 'none':
                # these aren't included in the listing
                continue
            if type != current_type:
                buf.write('\n')
                buf.write(type.capitalize())
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
            if args.pr:
                branch_name = f'rel-{new_version.major}-{new_version.minor}-{new_version.patch}'
                result = run(
                    ['git', 'checkout', '-b', branch_name],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(f'Failed to create branch {branch_name}', file=stderr)
                    print(result.stderr, file=stderr)
                    return self.exit(1)

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
                # Stage changes interactively
                result = run(['git', 'add', '-p'])
                if result.returncode != 0:
                    print('Failed to stage changes', file=stderr)
                    return self.exit(1)

                # Commit changes
                commit_message = f'Version {new_version.major}.{new_version.minor}.{new_version.patch} bump & changelog update'
                result = run(
                    ['git', 'commit', '-m', commit_message],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print('Failed to commit changes', file=stderr)
                    print(result.stderr, file=stderr)
                    return self.exit(1)

                # Push to origin
                result = run(
                    ['git', 'push', '-u', 'origin', branch_name],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print('Failed to push branch', file=stderr)
                    print(result.stderr, file=stderr)
                    return self.exit(1)

                # Create PR
                result = run(
                    [
                        'gh',
                        'pr',
                        'create',
                        '--title',
                        commit_message,
                        '--body',
                        buf,
                        '--assignee',
                        '@me',
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print('Failed to create PR', file=stderr)
                    print(result.stderr, file=stderr)
                    return self.exit(1)

                print(result.stdout)

        return new_version, buf
