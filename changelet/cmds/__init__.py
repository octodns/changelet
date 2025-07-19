#!/usr/bin/env python

from os.path import basename
from sys import argv

from changelet.base import Bump, Check, Create

cmds = {}


def register_cmd(command, klass):
    cmds[command] = klass


register_cmd('create', Create)
register_cmd('check', Check)
register_cmd('bump', Bump)


def general_usage(argv, msg=None):
    exe = basename(argv[0])
    options = ','.join(sorted(cmds.keys()))
    print(f'usage: {exe} {{{options}}} ...')
    if msg:
        print(msg)
    else:
        print(
            '''
Creates and checks or changelog entries, located in the .changelog directory.
Additionally supports updating CHANGELOG.md and bumping the package version
based on one or more entries in that directory.
'''
        )


def main(argv):
    try:
        Cmd = cmds[argv[1].lower()]
        argv.pop(1)
    except IndexError:
        general_usage(argv, 'missing command')
        exit(1)
        return
    except KeyError:
        if argv[1] in ('-h', '--help', 'help'):
            general_usage(argv)
            exit(0)
            return
        general_usage(argv, f'unknown command "{argv[1]}"')
        exit(1)
        return

    cmd = Cmd()
    args = cmd.parse(argv)
    cmd.run(args)


if __name__ == '__main__':  # pragma: no cover
    main(argv)
