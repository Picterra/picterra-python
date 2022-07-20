from ..helpers import CommandParser

class TrainCommandParser(CommandParser):
    def __init__(self, parser, logger):
        super().__init__('train', parser, logger)
        train_parser = self.parser.add_parser('train', help="Trains a detector")
        train_parser.add_argument("detector", help="ID of a detector", type=str)
        self.parsers_map = {
            'train': train_parser
        }

    def handle_command(self, options):
        super()
        self.logger.info('Training %s ..' % options.detector)
        self.client.train_detector(options.detector)
