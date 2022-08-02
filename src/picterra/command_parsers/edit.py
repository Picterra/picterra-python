from ..helpers import InvalidOptionError
from ..client import APIError, APIClient
import sys
import logging


logger = logging.getLogger(__name__)

def handle_command(options, client, parsers_map):
    if options.edit == 'raster':
        client.edit_raster(options.raster, name=options.name)
        logger.info('Edited raster whose id is %s' % options.raster)
    else:
        raise InvalidOptionError(parsers_map['edit'])


def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create parsers
    edit_parser = parser.add_parser('edit', help="Edit resources")
    edit_subparsers = edit_parser.add_subparsers(dest='edit')
    ## Edit raster
    edit_raster_parser = edit_subparsers.add_parser('raster', help="Edits a raster")
    edit_raster_parser.add_argument("raster", help="ID of the raster to edit", type=str)
    edit_raster_parser.add_argument(
        "--name", help="Name to give to the raster", type=str, required=False)
    parsers_map = {
        'edit': edit_parser,
        'raster': edit_raster_parser
    }
    edit_parser.set_defaults(func=lambda a: handle_command(a, client, parsers_map))
