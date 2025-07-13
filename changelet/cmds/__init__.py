#!/usr/bin/env python

from os.path import basename
from sys import argv

from changelet.base import Bump, Check, Create


def create(argv):
    cmd = Create()
    args = cmd.parse(argv)
    cmd.run(args)


def check(argv):
    cmd = Check()
    args = cmd.parse(argv)
    cmd.run(args)


def bump(argv):
    cmd = Bump()
    args = cmd.parse(argv)
    cmd.run(args)


cmds = {'create': create, 'check': check, 'bump': bump}


def general_usage(msg=None):
    global cmds

    exe = basename(argv[0])
    cmds = ','.join(sorted(cmds.keys()))
    print(f'usage: {exe} {{{cmds}}} ...')
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


def main():
    try:
        cmd = cmds[argv[1].lower()]
        argv.pop(1)
    except IndexError:
        general_usage('missing command')
        exit(1)
    except KeyError:
        if argv[1] in ('-h', '--help', 'help'):
            general_usage()
            exit(0)
        general_usage(f'unknown command "{argv[1]}"')
        exit(1)

    cmd(argv)


if __name__ == '__main__':
    main()
