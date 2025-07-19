#!/usr/bin/env python
#
#

from argparse import ArgumentParser
from sys import argv

from changelet.command import commands
from changelet.config import Config


def main(argv, exit_on_error=True):
    parser = ArgumentParser(add_help=True, exit_on_error=exit_on_error)

    subparsers = parser.add_subparsers(
        dest="command", help="Available sub-commands"
    )
    for command in commands.values():
        command_parser = subparsers.add_parser(
            command.name, description=command.description
        )
        command.configure(command_parser)

    args = parser.parse_args(argv[1:])
    print(args)

    config = Config.build()
    print(config)


if __name__ == '__main__':  # pragma: no cover
    main(argv)
