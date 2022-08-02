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
from .command_parsers.create import set_parser as create_set_parser
from .command_parsers.delete import set_parser as set_delete_parser
from .command_parsers.detect import set_parser as set_detect_parser
from .command_parsers.download import set_parser as set_download_parser
from .command_parsers.edit import set_parser as set_edit_parser
from .command_parsers.list import set_parser as set_list_parser
from .command_parsers.train import set_parser as set_train_parser
from .helpers import InvalidOptionError

from pkg_resources import get_distribution

logger = logging.getLogger(__name__)


__version__ = get_distribution('picterra').version

def parse_args(args):
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='picterra', description='Picterra API wrapper CLI tool', epilog='© Picterra '+ str(date.today().year))
    # Parser for version and verbosity
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument("-v", help="set output verbosity", action="store_true")
    # Default parser
    parser.set_defaults(func=lambda _: parser.print_help())
    # Create the parser for the subcommands
    subparsers = parser.add_subparsers(dest='command')
    # Create the parsers for the different commands
    create_set_parser(subparsers)
    set_delete_parser(subparsers)
    set_detect_parser(subparsers)
    set_download_parser(subparsers)
    set_edit_parser(subparsers)
    set_list_parser(subparsers)
    set_train_parser(subparsers)
    # Parse the command input
    args = parser.parse_args(args)
    # Verbosity increase (optional)
    if args.v:
        logging.basicConfig(level=logging.DEBUG)
    # Branch depending on command
    try:
        args.func(args)
    except InvalidOptionError as e:
        e.parser.print_help()
        sys.exit(0)
    return args


def main():
    try:
        parse_args(sys.argv[1:])
    except APIError as e:
        exit("\033[91m%s\033[00m" % e)


if __name__ == '__main__':
    main()
