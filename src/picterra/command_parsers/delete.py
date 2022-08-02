from ..helpers import InvalidOptionError
from ..client import APIError, APIClient
import sys
import logging


logger = logging.getLogger(__name__)

def handle_command(options, client, parsers_map):
    if options.delete == 'raster':
        client.delete_raster(options.raster)
        logger.info('Deleted raster whose id was %s' % options.raster)
    elif options.delete == 'detector':
        client.delete_detector(options.detector)
        logger.info('Deleted detector whose id was %s' % options.detector)
    elif options.delete == 'detection_area':
        logger.debug('Removing detection area from raster %s..' % options.raster)
        client.remove_raster_detection_areas(options.raster)
        logger.info('Removed detection area for raster whose id is %s' % options.raster)
    else:
        raise InvalidOptionError(parsers_map['delete'])


def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create parsers
    delete_parser = parser.add_parser('delete', help="Delete resources")
    delete_subparsers = delete_parser.add_subparsers(dest='delete')
    ## Delete raster
    delete_raster_parser = delete_subparsers.add_parser('raster', help="Removes a raster")
    delete_raster_parser.add_argument("raster", help="ID of the raster to delete", type=str)
    ## Delete detector
    delete_detector_parser = delete_subparsers.add_parser('detector', help="Removes a detector")
    delete_detector_parser.add_argument("detector", help="ID of the detector to delete", type=str)
    ## Delete detection areas
    delete_detectionarea_parser = delete_subparsers.add_parser(
        "detection_area", help="Removes the detection areas of raster, if any")
    delete_detectionarea_parser.add_argument(
        "raster", help="ID of the raster whose detection areas will be deleted", type=str)
    parsers_map = {
        'delete': delete_parser,
        'raster': delete_raster_parser,
        'detector': delete_detector_parser,
        'detection_area': delete_detectionarea_parser
    }
    delete_parser.set_defaults(func=lambda a: handle_command(a, client, parsers_map))
