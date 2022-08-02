from ..client import APIError, APIClient
import sys
import logging


logger = logging.getLogger(__name__)

def handle_command(options, client):
    logger.info('Training %s ..' % options.detector)
    client.train_detector(options.detector)

def set_parser(parser):
    try:
        client = APIClient()
    except APIError as e:
        sys.exit("\033[91m%s\033[00m" % e)
    # Create parsers
    train_parser = parser.add_parser('train', help="Trains a detector")
    train_parser.add_argument("detector", help="ID of a detector", type=str)
    train_parser.set_defaults(func=lambda a: handle_command(a, client))
