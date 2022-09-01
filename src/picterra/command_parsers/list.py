import json
from ..helpers import InvalidOptionError, CommandParser
import logging
from ..client import APIClient, APIError
import sys

logger = logging.getLogger(__name__)

def handle_command(options, client, parsers_map):
    if options.list == 'rasters':
        rasters = client.list_rasters(options.folder, options.search)
        if options.output == 'ids_only':
            for r in rasters:
                print(r['id'])
        else:  # default json
            print(json.dumps(rasters))
    elif options.list == 'detectors':
        print(json.dumps(client.list_detectors(options.search)))
    else:
        raise InvalidOptionError(parsers_map['list'])


def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create the parser for the "list" command
    list_parser = parser.add_parser('list', help="List resources")
    list_subparsers = list_parser.add_subparsers(dest='list')
    ## List rasters
    list_rasters_parser = list_subparsers.add_parser(
        'rasters', help="List user's rasters")
    list_rasters_parser.add_argument(
        "--output", help="Type of output", type=str, choices=['json', 'ids_only'], default='json')
    list_rasters_parser.add_argument(
        "--folder", help="Id of the folder/project whose rasters we want to list",
        type=str, required=False)
    list_rasters_parser.add_argument(
        "--search", help="String to search in the raster names to filter",
        type=str, required=False)
    ## List detectors
    list_detectors_parser = list_subparsers.add_parser(
        'detectors', help="List user's detectors")
    list_detectors_parser.add_argument(
        "--search", help="String to search in the detector names to filter",
        type=str, required=False)
    # Parsers mapping
    parsers_map = {
        'list': list_parser,
        'rasters': list_rasters_parser,
        'detectors': list_detectors_parser
    }
    list_parser.set_defaults(func=lambda a: handle_command(a, client, parsers_map))


