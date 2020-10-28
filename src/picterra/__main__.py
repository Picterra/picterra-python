"""
This file allows to run the module as a script

If adding commands, please follow this conventions for positional (required) args:

python -m picterra <COMMAND> [<SUBCOMMAND/RESOURCE>] INPUT_FILE RASTER DETECTOR OUTPUT_FILE
"""


import argparse
import logging
import json
import sys
import pprint

from .client import APIClient, APIError


logger = logging.getLogger(__name__)


def parse_args(args):
    # create the top-level parser
    parser = argparse.ArgumentParser(prog='picterra', epilog='© Picterra 2020')

    # Parser for version and verbosity
    parser.add_argument('--version', action='version', version='1.0.0')
    parser.add_argument("-v", help="set output verbosity", action="store_true")

    # create the parser for the subcommands
    subparsers = parser.add_subparsers(dest='command')

    # create the parser for the "list" command
    list_parser = subparsers.add_parser('list', help="List resources")
    list_parser.add_argument(
        'resource', help="List either detectors or rasters in your account",
        type=str, choices=['rasters', 'detectors'])

    # create the parser for the "detect" command
    detect_parser = subparsers.add_parser('detect', help="Predict on a raster with a detector")
    detect_parser.add_argument("raster", help="ID of a raster", type=str)
    detect_parser.add_argument("detector", help="ID of a detector", type=str)
    detect_parser.add_argument(
        "output_file", help="Path of the file were results will be saved", type=str)

    # create the parser for the "train" command
    train_parser = subparsers.add_parser('train', help="Trains a detector")
    train_parser.add_argument("detector", help="ID of a detector", type=str)

    # create the parsers for the "create" command
    create_parser = subparsers.add_parser('create', help="Create resources")
    create_subparsers = create_parser.add_subparsers(dest='create')
    # create detector
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
        "--training-steps", metavar='',
        help="Number of steps while training the detector: an integer in the range 500..40000",
        type=int, default=500)
    create_detector_parser.add_argument(
        "-r", "--raster", help="ID(s) of the raster (s) to associate with the detector",
        type=str, required=False, nargs='+', default=[])
    # create raster
    create_raster_parser = create_subparsers.add_parser(
        'raster', help="Creates a raster, optionally adding it to a detector")
    create_raster_parser.add_argument("path", help="Path to the raster file", type=str)
    create_raster_parser.add_argument("--name", help="Name of the raster", type=str, required=False)
    create_raster_parser.add_argument(
        "--folder", help="Id of the folder/project to which the raster will be uploaded",
        type=str, required=False)
    create_raster_parser.add_argument(
        "-d", "--detector", help="ID(s) of the detector(s) to which we'll associate the raster",
        type=str, required=False, nargs='+', default=[])
    # create annotation
    create_annotation_parser = create_subparsers.add_parser(
        'annotation', help="Add an annotation to a raster for a given detector")
    create_annotation_parser.add_argument(
        "path", help="Path  to the geojson file containing the annotation geometries", type=str)
    create_annotation_parser.add_argument("raster", help="ID of a raster", type=str)
    create_annotation_parser.add_argument("detector", help="ID of a detector", type=str)
    create_annotation_parser.add_argument(
        "type", help="Type of the annotation", type=str,
        choices=['outline', 'training_area', 'testing_area', 'validation_area'])
    # create detection area
    create_detection_area_parser = create_subparsers.add_parser(
        'detection_area', help="Add a detection area to a raster")
    create_detection_area_parser.add_argument(
        "path", help="Path to the geojson file containing the detection area geometries",
        type=str)
    create_detection_area_parser.add_argument("raster", help="ID of a raster", type=str)

    # create the parsers for the "delete" command
    delete_parser = subparsers.add_parser('delete', help="Delete resources")
    delete_subparsers = delete_parser.add_subparsers(dest='delete')
    # delete raster
    delete_parser = delete_subparsers.add_parser('raster', help="Removes a raster")
    delete_parser.add_argument("raster", help="ID of the raster to delete", type=str)

    # parse input
    options = parser.parse_args(args)

    # Branching for non Action-related operations
    if options.v:
        logging.basicConfig(level=logging.DEBUG)
    if options.command == 'list':
        if options.resource == 'rasters':
            client = APIClient()
            pprint.pprint(client.list_rasters())
        elif options.resource == 'detectors':
            client = APIClient()
            pprint.pprint(client.list_detectors())
    elif options.command == 'train':
        client = APIClient()
        logger.info('Training %s ..' % options.detector)
        client.train_detector(options.detector)
    elif options.command == 'detect':
        client = APIClient()
        logger.info('Running %s on %s' % (options.detector, options.raster))
        logger.debug('Starting detection..')
        result_id = client.run_detector(options.detector, options.raster)
        client.download_result_to_file(result_id, options.output_file)
        logger.debug('Detection finished, writing result to %s' % options.output_file)
    elif options.command == 'create':
        if options.create == 'detector':
            if not (500 <= options.training_steps <= 40000):
                raise APIError("Training steps invalid value %d: must be in [%d, %d]" % (
                    options.training_steps, 500, 40000
                ))
            client = APIClient()
            logger.debug('Creating %s %sdetector with output %s and %d steps.' % (
                options.detection_type,
                ('\"%s\" ' % {options.name}) if options.name else '',
                options.output_type,
                options.training_steps)
            )
            detector_id = client.create_detector(
                options.name, options.detection_type,
                options.output_type, int(options.training_steps)
            )
            i = 0
            for i, r in enumerate(options.raster, 1):
                client.add_raster_to_detector(r, detector_id)
                logger.debug('Added raster %s to %s detector' % (r, detector_id))
            tmp = (', and added %d rasters to it' % i) if i else ''
            logger.info('Created new detector whose id is %s%s' % (detector_id, tmp))
            print(detector_id)  # return value
        elif options.create == 'raster':
            client = APIClient()
            logger.debug('Starting creation %sraster from %s and uploading to %s..' % (
                ('\"%s\" ' % options.name) if options.name else '',
                options.path,
                options.folder)
            )
            raster_id = client.upload_raster(options.path, options.name, options.folder)
            i = 0
            for i, detector_id in enumerate(options.detector, 1):
                client.add_raster_to_detector(raster_id, detector_id)
                logger.debug('Added raster %s to %s detector' % (raster_id, detector_id))
            tmp = (', and added to %d detectors' % i) if i else ''
            logger.info('Created new raster whose id is %s%s' % (raster_id, tmp))
            print(raster_id)  # return value
        elif options.create == 'annotation':
            client = APIClient()
            logger.debug('Set new %s annotation on %s raster for %s detector from %s' % (
                options.type, options.raster, options.detector, options.path))
            with open(options.path) as json_file:
                data = json.load(json_file)
            client.set_annotations(options.detector, options.raster, options.type, data)
            logger.info('Set new %s annotation on %s raster for %s detector' % (
                options.type, options.raster, options.detector))
        elif options.create == 'detection_area':
            client = APIClient()
            logger.debug('Setting detection area on raster %s from %s..' % (
                options.raster, options.path))
            client.set_raster_detection_areas_from_file(options.raster, options.path)
            logger.info('Created new detection area for raster whose id is %s' % options.raster)
    elif options.command == 'delete':
        if options.delete == 'raster':
            client = APIClient()
            client.delete_raster(options.raster)
            logger.info('Deleted raster whose id was %s' % options.raster)
    return options


def main():
    try:
        parse_args(sys.argv[1:])
    except APIError as e:
        exit("\033[91m%s\033[00m" % e)


main()
