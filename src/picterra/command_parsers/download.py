from ..helpers import InvalidOptionError
from ..client import APIError, APIClient
import sys
import logging


logger = logging.getLogger(__name__)

def handle_command(options, client, parsers_map):
    if options.download == 'raster':
        client.download_raster_to_file(options.raster, options.path)
        logger.info('Downloaded raster whose id is %s' % options.raster)
    else:
        raise InvalidOptionError(parsers_map['download'])


def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create parsers
    download_parser = parser.add_parser('download', help="Download resources")
    download_subparsers = download_parser.add_subparsers(dest='download')
    ## Download raster
    download_raster_parser = download_subparsers.add_parser('raster', help="Downloads a raster")
    download_raster_parser.add_argument("raster", help="ID of the raster to download", type=str)
    download_raster_parser.add_argument(
        "path", help="Path to the local file where the raster will be saved", type=str)
    parsers_map = {
        'download': download_parser,
        'raster': download_raster_parser
    }
    download_parser.set_defaults(func=lambda a: handle_command(a, client, parsers_map))
