#
#
#

from datetime import datetime
from importlib import import_module
from io import StringIO
from os.path import abspath, basename, join
from sys import exit, path

from changelet.entry import Entry


def _get_current_version(module_name, directory='.'):
    path.append(directory)
    module = import_module(module_name)
    # TODO: make sure this requires 3-part semantic version
    return tuple(int(v) for v in module.__version__.split('.', 2))


def _get_new_version(current_version, entries):
    try:
        bump_type = entries[0].type
    except IndexError:
        return None
    new_version = list(current_version)
    if bump_type == 'major':
        new_version[0] += 1
        new_version[1] = 0
        new_version[2] = 0
    elif bump_type == 'minor':
        new_version[1] += 1
        new_version[2] = 0
    elif bump_type == 'patch':
        new_version[2] += 1
    else:
        return None
    return tuple(new_version)


def _format_version(version):
    return '.'.join(str(v) for v in version)


class Bump:
    name = 'bump'
    description = (
        'Builds a changelog update and calculates a new version number.'
    )

    def configure(self, parser):
        parser.add_argument(
            '--make-changes',
            action='store_true',
            help='Write changelog update and bump version number',
        )
        parser.add_argument(
            'title', nargs='+', help='A short title/quip for the release title'
        )

    def exit(self, code):
        exit(code)

    def run(self, args, config, root='.'):
        buf = StringIO()

        module_name = basename(abspath(root)).replace('-', '_')

        buf.write('## ')
        current_version = _get_current_version(module_name)

        entries = sorted(Entry.load_all(config), reverse=True)

        new_version = _get_new_version(current_version, entries)
        if not new_version:
            print('No changelog entries found that would bump, nothing to do')
            return self.exit(1)
        new_version = _format_version(new_version)
        buf.write(new_version)
        buf.write(' - ')
        buf.write(datetime.now().strftime('%Y-%m-%d'))
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
            print(f'changelog={changelog}')
            with open(changelog) as fh:
                existing = fh.read()

            with open(changelog, 'w') as fh:
                fh.write(buf)
                fh.write(existing)

            init = join(root, module_name, '__init__.py')
            with open(init) as fh:
                existing = fh.read()

            current_version = _format_version(current_version)
            with open(init, 'w') as fh:
                fh.write(existing.replace(current_version, new_version))

            for entry in entries:
                entry.remove()

        return new_version, buf
