from ..helpers import InvalidOptionError
from ..client import APIError, APIClient
import sys
import logging
from argparse import ArgumentParser, ArgumentTypeError, Action
import re


logger = logging.getLogger(__name__)

def handle_command(options, client, parsers_map):
    if options.edit == 'raster':
        new_bandspec = None
        if options.ranges or (options.red or options.green or options.blue):
            resp = client.sess.get(client._api_url('rasters/%s/' % options.raster))
            if not resp.ok:
                raise APIError(resp.text)
            old_bandspec = resp.json().get('multispectral_band_specification', None)
            if old_bandspec:
                new_bandspec = old_bandspec
                if options.red is not None:
                    new_bandspec['vizbands'][0] = options.red
                if options.green is not None:
                    new_bandspec['vizbands'][1] = options.green
                if options.blue is not None:
                    new_bandspec['vizbands'][2] = options.blue
                if options.ranges:
                    new_bandspec['ranges'] = options.ranges
        client.edit_raster(
            options.raster, name=options.name,
            multispectral_band_specification=new_bandspec)
        logger.info('Edited raster whose id is %s' % options.raster)
    else:
        raise InvalidOptionError(parsers_map['edit'])


class BandRange(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        lst = []
        for string in values:
            m = re.match(r'^(\d+)(?:\:(\d+))?$', string)
            if not m:
                raise ArgumentTypeError("'" + string + "' is not a range. Expected forms like '120:542'.")
            start = int(m.group(1))
            end = int(m.group(2))
            if start >= end:
                raise ArgumentTypeError("Invalid range from " + str(start) + " to " + str(end))
            lst.append([start, end])
            setattr(namespace, self.dest, lst)


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
    edit_raster_parser.add_argument(
        "--red", help="Index for the Red band", type=int, required=False)
    edit_raster_parser.add_argument(
        "--green", help="Index for the Green band", type=int, required=False)
    edit_raster_parser.add_argument(
        "--blue", help="Index for the Blue band", type=int, required=False,)
    edit_raster_parser.add_argument(
        '--ranges', action=BandRange, nargs='*',
        help="List of ranges in the form 334:444, e.g. '0:334 400:600 566:888 1233:9000'")
    parsers_map = {
        'edit': edit_parser,
        'raster': edit_raster_parser
    }
    edit_parser.set_defaults(func=lambda a: handle_command(a, client, parsers_map))
