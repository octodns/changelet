#
#
#


from datetime import datetime
from json import loads
from logging import getLogger
from subprocess import PIPE, run

from .pr import Pr


class GitHubCli:

    def __init__(self, repo=None, max_lookback=50):
        self.log = getLogger('GitHubCli[{repo}]')
        self.log.info('__init__: repo=%s, max_lookback=%d', repo, max_lookback)
        self.repo = repo
        self.max_lookback = max_lookback

        self._prs = None

    def prs(self, root, directory):
        # we're making an assumption here that we'll always be called with the
        # same root & directory so we can use them once and cache the results.
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
                    if f['path'].startswith(directory)
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

    def pr_by_id(self, root, directory, id):
        return self.prs(root=root, directory=directory).get(id)

    def pr_by_filename(self, root, directory, filename):
        return self.prs(root=root, directory=directory).get(filename)

    def changelog_entries_in_branch(self, root, directory):
        # TODO: automatically figure our main branch or configure it
        result = run(
            ['git', 'diff', '--name-only', 'origin/main'],
            check=False,
            stdout=PIPE,
        )
        return {
            l
            for l in result.stdout.decode('utf-8').split()
            if l.endswith('.md') and l.startswith(directory)
        }

    def add_file(self, filename):
        run(['git', 'add', filename], check=True)

    def commit(self, description):
        run(['git', 'commit', '-m', description], check=True)

    def __repr__(self):
        return f'GitHubCli<repo={self.repo}, max_lookback={self.max_lookback}>'
