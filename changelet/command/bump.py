#
#
#

from datetime import datetime
from importlib import import_module
from io import StringIO
from os.path import abspath, basename, join
from sys import exit, path

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
            'title', nargs='*', help='A short title/quip for the release title'
        )

    def exit(self, code):
        exit(code)

    def run(self, args, config, root='.'):
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
        if not args.make_changes:
            print(f'New version number {new_version}\n')
            print(buf)
            self.exit(0)
        else:
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

        return new_version, buf
