#
#
#

from datetime import datetime
from unittest import TestCase

from changelet.pr import Pr


class TestPr(TestCase):

    def test_pr(self):
        id = 42
        text = '#{id}'
        url = f'https://github.com/octodns/changelet/pull/{id}'
        merged_at = datetime(2025, 7, 1, 1, 2, 3)
        pr = Pr(id=id, text=text, url=url, merged_at=merged_at)

        self.assertEqual(url, pr.plain)
        self.assertEqual(f'[{text}]({url})', pr.markdown)
