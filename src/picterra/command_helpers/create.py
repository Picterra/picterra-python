from argparse import ArgumentTypeError
from datetime import datetime
import json
from ..client import APIError
from ..helpers import InvalidOptionError, CommandParser

def _raster_datetime_name() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _create_remote_raster_type(coords_string):
        coords = [float(item) for item in coords_string.split(',')]
        if len(coords) != 4:
            raise ArgumentTypeError(
                'Expected a bbox of exactly 4 coordinates, got %d' % len(coords)
            )
        for c in (coords[0], coords[2]):
            if not -180.0 <= c <= 180.0:
                raise ArgumentTypeError(
                    'Expected a valid Longitude (decimal between -180.0 and 180.0)'
                )
        for c in (coords[1], coords[3]):
            if not -90.0 <= c <= 90.0:
                raise ArgumentTypeError(
                    'Expected a valid Latitude (decimal between -90.0 and 90.0)'
                )
        if coords[0] >= coords[2] or coords[1] >= coords[3]:
            raise ArgumentTypeError(
                'Expected coordinates in "min Long , min Lat , max Long , max Lat" order'
            )
        return coords

class CreateCommandParser(CommandParser):

    def __init__(self, parser, logger):
        super().__init__('create', parser, logger)
        create_parser = self.parser.add_parser('create', help="Create resources")
        create_subparsers = create_parser.add_subparsers(dest='create')
        ## Create detector
        create_detector_parser = create_subparsers.add_parser(
            'detector', help="Creates a detector, optionally adding some existing raster to it")
        create_detector_parser.add_argument("--name", help="Name of the detector", type=str)
        create_detector_parser.add_argument(
            "--detection-type", help="Detection type of the detector",
            type=str, choices=['count', 'segmentation'], default='count')
        create_detector_parser.add_argument(
            "--output-type", help="Output type of the detector",
            type=str, choices=['polygon', 'bbox'], default='polygon')
        create_detector_parser.add_argument(
            "--training-steps", type=int, default=500,
            help="Number of steps while training the detector: an integer in the range 500..40000")
        create_detector_parser.add_argument(
            "-r", "--raster", help="ID(s) of the raster (s) to associate with the detector",
            type=str, required=False, nargs='+', default=[])
        ## Create raster
        create_raster_parser = create_subparsers.add_parser(
            'raster', help="Creates a raster, optionally adding it to a detector")
        create_raster_subparsers = create_raster_parser.add_subparsers(dest='raster')
        ### Create raster (from file)
        create_raster_from_file_parser = create_raster_subparsers.add_parser(
            'file', help="Uploads raster from a local file")
        create_raster_from_file_parser.add_argument("path", help="Path to the raster file", type=str)
        create_raster_from_file_parser.add_argument(
            "--name", help="Name to give to the raster",
            type=str, required=False, default=_raster_datetime_name())
        create_raster_from_file_parser.add_argument(
            "--folder", help="Id of the folder/project to which the raster will be uploaded",
            type=str, required=False)
        create_raster_from_file_parser.add_argument(
            "-d", "--detector", help="ID(s) of the detector(s) to which we'll associate the raster",
            type=str, required=False, nargs='+', default=[])
        create_raster_from_file_parser.add_argument(
            '--multispectral', default=False, action='store_true',
            help=" If True, the raster is in multispectral mode and can have an associated band specification")
        ### Create raster (from remote imagery server)
        create_raster_from_remote_parser = create_raster_subparsers.add_parser(
            'remote', help="Uploads raster from a remote imagery server")
        create_raster_from_remote_parser.add_argument(
            "type", help="Type of the imagery server", type=str, choices=['wms', 'xyz'])
        create_raster_from_remote_parser.add_argument("url", help="URL of the imagery server", type=str)
        create_raster_from_remote_parser.add_argument(
            "resolution", help="Spatial resolution (GSD) of the raster to upload, in meters",
            type=float)
        create_raster_from_remote_parser.add_argument(
            # https://bugs.python.org/issue14074, so we use a comma-separated list
            "bbox", type=_create_remote_raster_type,
            help="Comma(\",\")-delimited list of coordinates representing the bounding box for " +
            "the raster, i.e. an area defined by two longitudes " +
            "(decimal between -180.0 and 180.0) and two latitudes (decimal between -90.0 and 90.0)" +
            "in the following order: min Longitude , min Latitude , max Longitude , max Latitude")
        create_raster_from_remote_parser.add_argument(
            "--name", help="Name to give to the raster", type=str, required=False)
        create_raster_from_remote_parser.add_argument(
            "--credentials",
            help="Credentials for the imagery server in the 'user:password' format",
            type=str, required=False)
        create_raster_from_remote_parser.add_argument(
            "--folder", help="Id of the folder/project to which the raster will be uploaded",
            type=str, required=False)
        create_raster_from_remote_parser.add_argument(
            "-d", "--detector", help="ID(s) of the detector(s) to which we'll associate the raster",
            type=str, required=False, nargs='+', default=[])
        ## Create annotation
        create_annotation_parser = create_subparsers.add_parser(
            'annotation', help="Add an annotation to a raster for a given detector")
        create_annotation_parser.add_argument(
            "path", help="Path  to the geojson file containing the annotation geometries", type=str)
        create_annotation_parser.add_argument("raster", help="ID of a raster", type=str)
        create_annotation_parser.add_argument("detector", help="ID of a detector", type=str)
        create_annotation_parser.add_argument(
            "type", help="Type of the annotation", type=str,
            choices=['outline', 'training_area', 'testing_area', 'validation_area'])
        ## Create detection area
        create_detection_area_parser = create_subparsers.add_parser(
            'detection_area', help="Add a detection area to a raster")
        create_detection_area_parser.add_argument(
            "path", help="Path to the geojson file containing the detection area geometries",
            type=str)
        create_detection_area_parser.add_argument("raster", help="ID of a raster", type=str)
        self.parsers_map = {
            'create': create_parser,
            'detector': create_detector_parser,
            'raster': create_raster_parser,
            'detection_area': create_detection_area_parser,
            'annotation': create_annotation_parser,
            'raster__file': create_raster_from_file_parser,
            'raster__remote': create_raster_from_remote_parser
        }

    def handle_command(self, options):
        super()
        if options.create == 'detector':
            if not (500 <= options.training_steps <= 40000):
                raise APIError("Training steps invalid value %d: must be in [%d, %d]" % (
                    options.training_steps, 500, 40000
                ))
            self.logger.debug('Creating %s %sdetector with output %s and %d steps.' % (
                options.detection_type,
                ('\"%s\" ' % {options.name}) if options.name else '',
                options.output_type,
                options.training_steps)
            )
            detector_id = self.client.create_detector(
                options.name, options.detection_type,
                options.output_type, int(options.training_steps)
            )
            if options.raster:
                i = 0
                for i, r in enumerate(options.raster, 1):
                    self.client.add_raster_to_detector(r, detector_id)
                    self.logger.debug('Added raster %s to %s detector' % (r, detector_id))
                tmp = (', and added %d rasters to it' % i) if i else ''
            else:
                tmp = ''
            self.logger.info('Created new detector whose id is %s%s' % (detector_id, tmp))
            print(detector_id)  # return value
        elif options.create == 'raster':
            # raster_name = options.name or _raster_datetime_name()
            if options.raster == 'file':
                self.logger.debug('Starting creation %s raster from %s and uploading to %s..' % (
                    ('\"%s\" ' % options.name),
                    options.path,
                    options.folder)
                )
                raster_id = self.client.upload_raster(
                    options.path, options.name, options.folder, multispectral=options.multispectral)
            elif options.raster == 'remote':
                footprint = {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [options.bbox[0], options.bbox[1]],
                            [options.bbox[2], options.bbox[1]],
                            [options.bbox[2], options.bbox[3]],
                            [options.bbox[0], options.bbox[3]],
                            [options.bbox[0], options.bbox[1]]
                        ]
                    ]
                }
                self.logger.debug('Creating %s raster from %s @%s GSD with footprint %s..' % (
                    options.name, options.url, options.resolution, footprint))
                raster_id = self.client.upload_remote_raster(
                    options.type, options.url, options.resolution, footprint,
                    options.credentials, options.name, options.folder)
            else:
                raise InvalidOptionError(self.parsers_map['raster'])
            if options.detector:
                i = 0
                for i, detector_id in enumerate(options.detector, 1):
                    self.client.add_raster_to_detector(raster_id, detector_id)
                    self.logger.debug('Added raster %s to %s detector' % (raster_id, detector_id))
                tmp = (', and added to %d detectors' % i) if i else ''
            else:
                tmp = ''
            self.logger.info('Created new raster whose id is %s%s' % (raster_id, tmp))
            print(raster_id)  # return value
        elif options.create == 'annotation':
            self.logger.debug('Set new %s annotation on %s raster for %s detector from %s' % (
                options.type, options.raster, options.detector, options.path))
            with open(options.path) as json_file:
                data = json.load(json_file)
            self.client.set_annotations(options.detector, options.raster, options.type, data)
            self.logger.info('Set new %s annotation on %s raster for %s detector' % (
                options.type, options.raster, options.detector))
        elif options.create == 'detection_area':
            self.logger.debug('Setting detection area on raster %s from %s..' % (
                options.raster, options.path))
            self.client.set_raster_detection_areas_from_file(options.raster, options.path)
            self.logger.info('Created new detection area for raster whose id is %s' % options.raster)
        else:
            raise InvalidOptionError(self.parsers_map['create'])
