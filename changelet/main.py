#!/usr/bin/env python
#
#

from argparse import ArgumentParser
from sys import argv

from changelet.command import commands
from changelet.config import Config


def main(argv, exit_on_error=True):
    parser = ArgumentParser(add_help=True, exit_on_error=exit_on_error)
    parser.add_argument('-c', '--config', help='TODO')

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available sub-commands"
    )
    for command in commands.values():
        command_parser = subparsers.add_parser(
            command.name, description=command.description
        )
        command.configure(command_parser)

    args = parser.parse_args(argv[1:])

    config = Config.build(config=args.config)
    try:
        command = commands[args.command]
    except KeyError:  # pragma: no cover
        # python < 3.12 argparse exit_on_error doesn't cover all cases, and in
        # testing we have to mock its exit to noop it. that results in parse
        # returning args w/o a command. This handles that case w/o blowing up
        pass
    else:
        command.run(args=args, config=config)


if __name__ == '__main__':  # pragma: no cover
    main(argv)
