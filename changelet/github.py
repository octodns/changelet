#
#
#


from datetime import datetime
from json import loads
from logging import getLogger
from os.path import isdir
from subprocess import PIPE, run

from .pr import Pr


class GitHubCli:

    def __init__(self, directory, repo=None, max_lookback=50):
        self.log = getLogger('GitHubCli[{repo}]')
        self.log.info(
            '__init__: directory=%s, max_lookback=%d', directory, max_lookback
        )
        self.repo = repo
        self.directory = directory
        self.max_lookback = max_lookback

        self._prs = None

    @property
    def prs(self):
        if self._prs is None:
            # will be indexed by both id & filename
            prs = {}

            cmd = [
                'gh',
                'pr',
                'list',
                '--base',
                'main',
                '--state',
                'merged',
                f'--limit={self.max_lookback}',
                '--json',
                'files,mergedAt,number',
            ]
            if self.repo:
                cmd.extend(('--repo', f'{self.repo}'))
            result = run(cmd, check=True, stdout=PIPE)

            for pr in loads(result.stdout):
                number = pr['number']
                url = f'https://github.com/{self.repo}/pull/{number}'
                merged_at = datetime.fromisoformat(pr['mergedAt'])

                files = [
                    f['path']
                    for f in pr['files']
                    if f['path'].startswith(self.directory)
                ]
                if not files:
                    # no changelog entries, ignore it
                    continue

                pr = Pr(
                    id=number, text=f'#{number}', url=url, merged_at=merged_at
                )
                prs[number] = pr
                for filename in files:
                    prs[filename] = pr
            self._prs = prs

        return self._prs

    def pr_by_id(self, id):
        return self.prs.get(id)

    def pr_by_filename(self, filename):
        return self.prs.get(filename)

    def changelog_entries_in_branch(self):
        # TODO: automatically figure our main branch or configure it
        if not isdir(self.directory):
            return set()
        result = run(
            ['git', 'diff', '--name-only', 'origin/main', self.directory],
            check=False,
            stdout=PIPE,
        )
        return {
            l
            for l in result.stdout.decode('utf-8').split()
            if l.endswith('.md')
        }

    def add_file(self, filename):
        run(['git', 'add', filename], check=True)

    def __repr__(self):
        return f'GitHubCli<directory={self.directory}, repo={self.repo}, max_lookback={self.max_lookback}>'
