"""
This file allows to run the module as a script

If adding commands, please follow this conventions for positional (required) args:

python -m picterra <COMMAND> [<SUBCOMMAND>] INPUT_FILE RASTER DETECTOR OUTPUT_FILE
"""


import argparse
import logging
import json
import sys
import os
from datetime import datetime

from .client import APIClient, APIError, CHUNK_SIZE_BYTES


logger = logging.getLogger(__name__)


def _read_in_chunks(file_object, chunk_size=CHUNK_SIZE_BYTES):
    """Generator to read a file piece by piece."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def _raster_datetime_name() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_args(args):
    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog='picterra', description='Picterra API wrapper CLI tool', epilog='© Picterra 2020')

    # Parser for version and verbosity
    parser.add_argument('--version', action='version', version='1.0.0')
    parser.add_argument("-v", help="set output verbosity", action="store_true")

    # create the parser for the subcommands
    subparsers = parser.add_subparsers(dest='command')

    # Create the parser for the "list" command
    list_parser = subparsers.add_parser('list', help="List resources")
    list_subparsers = list_parser.add_subparsers(dest='list')
    # List rasters
    list_rasters_parser = list_subparsers.add_parser(
        'rasters', help="List user's rasters")
    list_rasters_parser.add_argument(
        "--output", help="Type of output", type=str, choices=['json', 'ids_only'], default='json')
    list_rasters_parser.add_argument(
        "--folder", help="Id of the folder/project whose rasters we want to list",
        type=str, required=False)
    # List detectors
    list_subparsers.add_parser(
        'detectors', help="List user's detectors")

    # create the parser for the "detect" command
    detect_parser = subparsers.add_parser(
        'detect',
        help=(
            'Predict on a raster with a detector, either returning the result URL' +
            ' or saving it to a local file'))
    detect_parser.add_argument("raster", help="ID of a raster", type=str)
    detect_parser.add_argument("detector", help="ID of a detector", type=str)
    detect_parser.add_argument(
        "--output-type", help="How results are presented to the output",
        type=str, choices=["url", "geometries"], default="url", required=False)
    detect_parser.add_argument(
        "--output-file", type=str, required=False,
        help=(
            "Path of the file in which the output should be saved. " +
            "If this is not set, the output will be printed to stdout"
        )
    )
    # create the parser for the "train" command
    train_parser = subparsers.add_parser('train', help="Trains a detector")
    train_parser.add_argument("detector", help="ID of a detector", type=str)

    # create the parsers for the "create" commands
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
    delete_raster_parser = delete_subparsers.add_parser('raster', help="Removes a raster")
    delete_raster_parser.add_argument("raster", help="ID of the raster to delete", type=str)
    # delete detector
    delete_detector_parser = delete_subparsers.add_parser('detector', help="Removes a detector")
    delete_detector_parser.add_argument("detector", help="ID of the detector to delete", type=str)
    # delete detection areas
    delete_detectionarea_parser = delete_subparsers.add_parser(
        "detection_area", help="Removes the detection areas of raster, if any")
    delete_detectionarea_parser.add_argument(
        "raster", help="ID of the raster whose detection areas will be deleted", type=str)

    # create the parsers for the "download" command
    download_parser = subparsers.add_parser('download', help="Download resources")
    download_subparsers = download_parser.add_subparsers(dest='download')
    # download raster
    download_raster_parser = download_subparsers.add_parser('raster', help="Downloads a raster")
    download_raster_parser.add_argument("raster", help="ID of the raster to download", type=str)
    download_raster_parser.add_argument(
        "path", help="Path to the local file where the raster will be saved", type=str)

    # parse input
    options = parser.parse_args(args)

    # Verbosity increase (optional)
    if options.v:
        logging.basicConfig(level=logging.DEBUG)

    # Create client and branch depending on command
    if options.command:
        client = APIClient()
    if options.command == 'list':
        if options.list == 'rasters':
            rasters = client.list_rasters(options.folder)
            if options.output == 'ids_only':
                for r in rasters:
                    print(r['id'])
            else:  # default json
                print(json.dumps(rasters))
        elif options.list == 'detectors':
            print(json.dumps(client.list_detectors()))
    elif options.command == 'train':
        logger.info('Training %s ..' % options.detector)
        client.train_detector(options.detector)
    elif options.command == 'detect':
        logger.info('Running %s on %s' % (options.detector, options.raster))
        logger.debug('Starting detection..')
        operation_id = client.run_detector(options.detector, options.raster)
        if options.output_type == 'geometries':   # outputting/saving result geometries
            if options.output_file:
                logger.debug('Detection finished, writing result to %s' % options.output_file)
                client.download_result_to_feature_collection(operation_id, options.output_file)
            else:
                from tempfile import mkstemp
                fd, path = mkstemp()
                client.download_result_to_feature_collection(operation_id, path)
                logger.debug('Detection finished, outputting result data')
                with open(path) as f:
                    for piece in _read_in_chunks(f):
                        # return values
                        print(piece, end='')
                # cleanup
                os.close(fd)
                os.unlink(path)
        else:  # URL
            if options.output_file:
                client.download_operation_results_to_file(operation_id, options.output_file)
                logger.debug('Detection finished, writing result URL to %s' % options.output_file)
            else:
                url = client.get_operation_results_url(operation_id)
                logger.debug('Detection finished, outputting result URL')
                # return value
                print(url)
    elif options.command == 'create':
        if options.create == 'detector':
            if not (500 <= options.training_steps <= 40000):
                raise APIError("Training steps invalid value %d: must be in [%d, %d]" % (
                    options.training_steps, 500, 40000
                ))
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
            raster_name = options.name or _raster_datetime_name()
            logger.debug('Starting creation %s raster from %s and uploading to %s..' % (
                '\"%s\" ' % raster_name,
                options.path,
                options.folder)
            )
            raster_id = client.upload_raster(options.path, raster_name, options.folder)
            i = 0
            for i, detector_id in enumerate(options.detector, 1):
                client.add_raster_to_detector(raster_id, detector_id)
                logger.debug('Added raster %s to %s detector' % (raster_id, detector_id))
            tmp = (', and added to %d detectors' % i) if i else ''
            logger.info('Created new raster whose id is %s%s' % (raster_id, tmp))
            print(raster_id)  # return value
        elif options.create == 'annotation':
            logger.debug('Set new %s annotation on %s raster for %s detector from %s' % (
                options.type, options.raster, options.detector, options.path))
            with open(options.path) as json_file:
                data = json.load(json_file)
            client.set_annotations(options.detector, options.raster, options.type, data)
            logger.info('Set new %s annotation on %s raster for %s detector' % (
                options.type, options.raster, options.detector))
        elif options.create == 'detection_area':
            logger.debug('Setting detection area on raster %s from %s..' % (
                options.raster, options.path))
            client.set_raster_detection_areas_from_file(options.raster, options.path)
            logger.info('Created new detection area for raster whose id is %s' % options.raster)
    elif options.command == 'delete':
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
    elif options.command == 'download':
        if options.download == 'raster':
            client.download_raster_to_file(options.raster, options.path)
            logger.info('Downloaded raster whose id is %s' % options.raster)
    return options


def main():
    try:
        parse_args(sys.argv[1:])
    except APIError as e:
        exit("\033[91m%s\033[00m" % e)


if __name__ == '__main__':
    main()
