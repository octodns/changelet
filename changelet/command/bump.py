#
#
#

from datetime import datetime
from importlib import import_module
from io import StringIO
from json import loads
from os import getcwd, listdir, remove
from os.path import basename, join
from subprocess import PIPE, run
from sys import exit, path

from yaml import safe_load


def _get_current_version(module_name, directory='.'):
    path.append(directory)
    module = import_module(module_name)
    # TODO: make sure this requires 3-part semantic version
    return tuple(int(v) for v in module.__version__.split('.', 2))


class _ChangeMeta:
    _pr_cache = None

    @classmethod
    def get(cls, filepath, data):
        if 'pr' in data:
            return data['pr'], datetime(year=1970, month=1, day=1)
        if cls._pr_cache is None:
            result = run(
                [
                    'gh',
                    'pr',
                    'list',
                    '--base',
                    'main',
                    '--state',
                    'merged',
                    '--limit=50',
                    '--json',
                    'files,mergedAt,number',
                ],
                check=True,
                stdout=PIPE,
            )
            cls._pr_cache = {}
            for pr in loads(result.stdout):
                for file in pr['files']:
                    path = file['path']
                    if path.startswith('.changelog'):
                        cls._pr_cache[path] = (
                            pr['number'],
                            datetime.fromisoformat(pr['mergedAt']).replace(
                                tzinfo=None
                            ),
                        )

        try:
            return cls._pr_cache[filepath]
        except KeyError:
            # couldn't find a PR with the changelog file in it
            return None, datetime(year=1970, month=1, day=1)


def _get_changelogs(directory):
    ret = []
    for filename in sorted(listdir(directory)):
        if not filename.endswith('.md'):
            continue
        filepath = join(directory, filename)
        with open(filepath) as fh:
            pieces = fh.read().split('---\n')
            data = safe_load(pieces[1])
            md = pieces[2]
            if md[-1] == '\n':
                md = md[:-1]
        pr, time = _ChangeMeta.get(filepath, data)
        if pr is None:
            continue
        ret.append(
            {
                'filepath': filepath,
                'md': md,
                'pr': pr,
                'time': time,
                'type': data.get('type', '').lower(),
            }
        )

    ordering = {'major': 3, 'minor': 2, 'patch': 1, 'none': 0, '': 0}
    ret.sort(key=lambda c: (ordering[c['type']], c['time']), reverse=True)
    return ret


def _get_new_version(current_version, changelogs):
    try:
        bump_type = changelogs[0]['type']
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

    def run(self, args, config, directory='.'):
        buf = StringIO()

        cwd = getcwd()
        module_name = basename(cwd).replace('-', '_')

        buf.write('## ')
        current_version = _get_current_version(module_name)
        changelogs = _get_changelogs(join(directory, '.changelog'))
        new_version = _get_new_version(current_version, changelogs)
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
        for changelog in changelogs:
            md = changelog['md']
            if not md:
                continue

            _type = changelog['type']
            if _type == 'none':
                # these aren't included in the listing
                continue
            if _type != current_type:
                buf.write('\n')
                buf.write(_type.capitalize())
                buf.write(':\n')
                current_type = _type
            buf.write('* ')
            buf.write(md)

            pr = changelog['pr']
            if pr:
                pr = str(pr)
                buf.write(' [#')
                buf.write(pr)
                buf.write('](https://github.com/octodns/')
                buf.write(module_name)
                buf.write('/pull/')
                buf.write(pr)
                buf.write(')')

            buf.write('\n')

        buf.write('\n')

        buf = buf.getvalue()
        if not args.make_changes:
            print(f'New version number {new_version}\n')
            print(buf)
            return self.exit(0)
        else:
            changelog = join(directory, 'CHANGELOG.md')
            print(f'changelog={changelog}')
            with open(changelog) as fh:
                existing = fh.read()

            with open(changelog, 'w') as fh:
                fh.write(buf)
                fh.write(existing)

            init = join(directory, module_name, '__init__.py')
            with open(init) as fh:
                existing = fh.read()

            current_version = _format_version(current_version)
            with open(init, 'w') as fh:
                fh.write(existing.replace(current_version, new_version))

            for changelog in changelogs:
                filepath = join(directory, changelog['filepath'])
                remove(filepath)

        return new_version, buf
