#
#
#

from shutil import rmtree
from tempfile import mkdtemp


class TemporaryDirectory(object):
    def __init__(self, delete_on_exit=True):
        self.delete_on_exit = delete_on_exit

    def __enter__(self):
        self.dirname = mkdtemp()
        return self

    def __exit__(self, *args, **kwargs):
        if self.delete_on_exit:
            rmtree(self.dirname)
        else:
            raise Exception(self.dirname)


class AssertActionMixin:
    def assert_action(
        self, action, flags, default, nargs=0, required=False, choices=None
    ):
        self.assertEqual(flags, action.option_strings)
        self.assertEqual(default, action.default)
        if choices is not None:
            self.assertEqual(choices, set(action.choices))
        self.assertEqual(required, action.required)
        self.assertTrue(action.help)
