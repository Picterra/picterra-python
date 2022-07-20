"""
This file allows to run the module as a script

If adding commands, please follow this conventions for positional (required) args:

python -m picterra <COMMAND> [<SUBCOMMAND>] INPUT_FILE RASTER DETECTOR OUTPUT_FILE
"""


import argparse
import logging
import sys
from datetime import date

from .client import APIError
from .command_helpers.create import CreateCommandParser
from .command_helpers.delete import DeleteCommandParser
from .command_helpers.detect import DetectCommandParser
from .command_helpers.download import DownloadCommandParser
from .command_helpers.edit import EditCommandParser
from .command_helpers.list import ListCommandParser
from .command_helpers.train import TrainCommandParser
from .helpers import InvalidOptionError

from pkg_resources import get_distribution


logger = logging.getLogger(__name__)

__version__ = get_distribution('picterra').version

def parse_args(args):
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='picterra', description='Picterra API wrapper CLI tool', epilog=f'© Picterra {date.today().year}')
    # Parser for version and verbosity
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument("-v", help="set output verbosity", action="store_true")
    # Default parser
    parser.set_defaults(func=lambda _: parser.print_help())
    # Create the parser for the subcommands
    subparsers = parser.add_subparsers(dest='command')
    # Create the parsers for the different commands
    command_parsers = {
        'create': CreateCommandParser(subparsers, logger),
        'delete': DeleteCommandParser(subparsers, logger),
        'detect': DetectCommandParser(subparsers, logger),
        'download': DownloadCommandParser(subparsers, logger),
        'edit': EditCommandParser(subparsers, logger),
        'list': ListCommandParser(subparsers, logger),
        'train': TrainCommandParser(subparsers, logger)
    }
    # Parse the command input
    options = parser.parse_args(args)
    # Verbosity increase (optional)
    if options.v:
        logging.basicConfig(level=logging.DEBUG)
    # Branch depending on command
    try:
        cmd = options.command
        if cmd and cmd in command_parsers:
            command_parsers[cmd].handle_command(options)
        else:
            parser.print_help()
    except InvalidOptionError as e:
        e.parser.print_help()
        sys.exit(0)
    return options


def main():
    try:
        parse_args(sys.argv[1:])
    except APIError as e:
        exit("\033[91m%s\033[00m" % e)


if __name__ == '__main__':
    main()
