#
#
#

from enum import Enum

from yaml import safe_load


class EntryType(Enum):
    NONE = 'none'
    PATCH = 'patch'
    MINOR = 'minor'
    MAJOR = 'major'


class Entry:

    @classmethod
    def load(self, filename, provider):
        with open(filename, 'r') as fh:
            pieces = fh.read().split('---\n')
            data = safe_load(pieces[1])
            message = pieces[2]
            if message[-1] == '\n':
                message = message[:-1]
            if 'pr' in data:
                pr = provider.pr_by_id(data['pr'])
            else:
                pr = provider.pr_by_filename(filename)
            return Entry(
                filename=filename, type=data['type'], message=message, pr=pr
            )

    def __init__(self, type, message, pr=None, filename=None):
        self.type = type
        self.message = message
        self.pr = pr
        self.filename = filename

    def save(self, filename=None):
        if filename is None:
            filename = self.filename
        with open(filename, 'w') as fh:
            fh.write('---\ntype: ')
            fh.write(self.type)
            if self.pr:
                fh.write('\npr: ')
                fh.write(str(self.pr.id))
            fh.write('\n---\n')
            fh.write(self.message)
        self.filename = filename

    @property
    def text(self):
        if self.pr:
            return f'* {self.message} - {self.pr.plain}'
        return f'* {self.message}'

    @property
    def markdown(self):
        if self.pr:
            return f'* {self.message} - {self.pr.markdown}'
        return f'* {self.message}'

    def copy(self):
        return Entry(
            type=self.type,
            message=self.message,
            pr=self.pr,
            filename=self.filename,
        )

    def __eq__(self, other):
        return (self.filename, self.type, self.message) == (
            other.filename,
            other.type,
            other.message,
        )
