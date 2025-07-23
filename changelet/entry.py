#
#
#

from datetime import datetime
from enum import Enum
from os import listdir, makedirs, remove
from os.path import dirname, isdir, join

from yaml import safe_load


class EntryType(Enum):
    NONE = 'none'
    PATCH = 'patch'
    MINOR = 'minor'
    MAJOR = 'major'


class Entry:
    EPOCH = datetime(1970, 1, 1)
    ORDERING = {'major': 3, 'minor': 2, 'patch': 1, 'none': 0, '': 0}

    @classmethod
    def load(self, filename, config):
        with open(filename, 'r') as fh:
            pieces = fh.read().split('---\n')
            data = safe_load(pieces[1])
            description = pieces[2]
            if description[-1] == '\n':
                description = description[:-1]
            if 'pr' in data:
                pr = config.provider.pr_by_id(data['pr'])
            else:
                pr = config.provider.pr_by_filename(filename)
            return Entry(
                filename=filename,
                type=data['type'],
                description=description,
                pr=pr,
            )

    @classmethod
    def load_all(cls, config):
        directory = config.directory
        entries = []
        if isdir(directory):
            for filename in sorted(listdir(directory)):
                if not filename.endswith('.md'):
                    continue
                filename = join(directory, filename)
                entries.append(Entry.load(filename, config))
        return entries

    def __init__(self, type, description, pr=None, filename=None):
        self.type = type
        self.description = description
        self.pr = pr
        self.filename = filename

    @property
    def _ordering(self):
        return (
            self.ORDERING[self.type],
            self.pr.merged_at if self.pr else self.EPOCH,
        )

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        directory = dirname(filename)
        if not isdir(directory):
            makedirs(directory)
        with open(filename, 'w') as fh:
            fh.write('---\ntype: ')
            fh.write(self.type)
            if self.pr:
                fh.write('\npr: ')
                fh.write(str(self.pr.id))
            fh.write('\n---\n')
            fh.write(self.description)
        self.filename = filename

    def remove(self):
        if not self.filename:
            return False
        remove(self.filename)
        return True

    @property
    def text(self):
        if self.pr:
            return f'* {self.description} - {self.pr.plain}'
        return f'* {self.description}'

    @property
    def markdown(self):
        if self.pr:
            return f'* {self.description} - {self.pr.markdown}'
        return f'* {self.description}'

    def copy(self):
        return Entry(
            type=self.type,
            description=self.description,
            pr=self.pr,
            filename=self.filename,
        )

    def __lt__(self, other):
        return self._ordering < other._ordering
