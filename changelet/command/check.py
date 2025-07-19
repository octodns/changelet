#
#
#

from os.path import isdir, join
from subprocess import PIPE, run
from sys import exit, stderr


class Check:
    name = 'check'
    description = (
        'Checks to see if the current branch contains a changelog entry'
    )

    def configure(self, parser):
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
