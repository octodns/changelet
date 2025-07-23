#
#
#


class Pr:

    def __init__(self, id, text, url, merged_at):
        self.id = id
        self.text = text
        self.url = url
        self.merged_at = merged_at

    @property
    def plain(self):
        return f'{self.url}'

    @property
    def markdown(self):
        return f'[{self.text}]({self.url})'
