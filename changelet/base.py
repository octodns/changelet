#
#
#

from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import datetime
from importlib import import_module
from io import StringIO
from json import loads
from os import getcwd, listdir, makedirs, remove
from os.path import basename, isdir, join
from subprocess import PIPE, run
from sys import exit, path, stderr
from uuid import uuid4

from yaml import safe_load


class Create:

    def parse(self, argv, exit_on_error=True):
        prog = basename(argv.pop(0))
        parser = ArgumentParser(
            prog=f'{prog} create',
            description='Creates a new changelog entry.',
            add_help=True,
            formatter_class=RawTextHelpFormatter,
            exit_on_error=exit_on_error,
        )

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
            help='git add the newly created changelog entry',
        )
        parser.add_argument(
            'md',
            metavar='change-description-markdown',
            nargs='+',
            help='''A short description of the changes in this PR, suitable as an entry in
CHANGELOG.md. Should be a single line. Can include simple markdown formatting
and links.''',
        )
        return parser.parse_args(argv)

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


class Check:

    def parse(self, argv):
        argv
        return None

    def run(self, args, directory='.'):
        directory = join(directory, '.changelog')
        if isdir(directory):
            result = run(
                ['git', 'diff', '--name-only', 'origin/main', directory],
                check=False,
                stdout=PIPE,
            )
            entries = {
                l
                for l in result.stdout.decode('utf-8').split()
                if l.endswith('.md')
            }
            print(f'code={result.returncode}, entries={entries}')
            if not result.returncode and entries:
                exit(0)
                return True

        print(
            'PR is missing required changelog file, run changelet create',
            file=stderr,
        )
        exit(1)
        return False


def _get_current_version(module_name):
    cwd = getcwd()
    path.append(cwd)
    module = import_module(module_name)
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


def _get_changelogs():
    ret = []
    dirname = '.changelog'
    for filename in listdir(dirname):
        if not filename.endswith('.md'):
            continue
        filepath = join(dirname, filename)
        with open(filepath) as fh:
            pieces = fh.read().split('---\n')
            data = safe_load(pieces[1])
            md = pieces[2]
            if md[-1] == '\n':
                md = md[:-1]
        pr, time = _ChangeMeta.get(filepath, data)
        if not pr:
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
    else:
        new_version[2] += 1
    return tuple(new_version)


def _format_version(version):
    return '.'.join(str(v) for v in version)


class Bump:

    def parse(self, argv):
        prog = basename(argv.pop(0))
        parser = ArgumentParser(
            prog=f'{prog} bump',
            description='Builds a changelog update and calculates a new version number.',
            add_help=True,
        )

        parser.add_argument(
            '--make-changes',
            action='store_true',
            help='Write changelog update and bump version number',
        )
        parser.add_argument(
            'title', nargs='+', help='A short title/quip for the release title'
        )

        return parser.parse_args(argv)

    def run(self, args):
        buf = StringIO()

        cwd = getcwd()
        module_name = basename(cwd).replace('-', '_')

        buf.write('## ')
        current_version = _get_current_version(module_name)
        changelogs = _get_changelogs()
        new_version = _get_new_version(current_version, changelogs)
        if not new_version:
            print('No changelog entries found that would bump, nothing to do')
            exit(1)
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

        if not args.make_changes:
            print(f'New version number {new_version}\n')
            print(buf.getvalue())
            exit(0)

        with open('CHANGELOG.md') as fh:
            existing = fh.read()

        with open('CHANGELOG.md', 'w') as fh:
            fh.write(buf.getvalue())
            fh.write(existing)

        with open(f'{module_name}/__init__.py') as fh:
            existing = fh.read()

        current_version = _format_version(current_version)
        with open(f'{module_name}/__init__.py', 'w') as fh:
            fh.write(existing.replace(current_version, new_version))

        for changelog in changelogs:
            remove(changelog['filepath'])
