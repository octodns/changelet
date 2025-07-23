#
#
#

from .bump import Bump
from .check import Check
from .create import Create

commands = {}


def register(klass):
    commands[klass.name] = klass()


register(Bump)
register(Check)
register(Create)
