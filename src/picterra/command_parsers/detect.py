import os
from ..client import CHUNK_SIZE_BYTES
from ..client import APIError, APIClient
import sys
import logging


logger = logging.getLogger(__name__)


def _read_in_chunks(file_object, chunk_size=CHUNK_SIZE_BYTES):
    """Generator to read a file piece by piece."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data

def handle_command(options, client):
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


def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create parsers
    detect_parser = parser.add_parser(
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
    detect_parser.set_defaults(func=lambda a: handle_command(a, client))

