import json
from ..helpers import InvalidOptionError, CommandParser


class ListCommandParser(CommandParser):
    def __init__(self, parser, logger):
        super().__init__('list', parser, logger)
        # Create the parser for the "list" command
        list_parser = self.parser.add_parser('list', help="List resources")
        list_subparsers = list_parser.add_subparsers(dest='list')
        ## List rasters
        list_rasters_parser = list_subparsers.add_parser(
            'rasters', help="List user's rasters")
        list_rasters_parser.add_argument(
            "--output", help="Type of output", type=str, choices=['json', 'ids_only'], default='json')
        list_rasters_parser.add_argument(
            "--folder", help="Id of the folder/project whose rasters we want to list",
            type=str, required=False)
        ## List detectors
        list_detectors_parser = list_subparsers.add_parser(
            'detectors', help="List user's detectors")
        self.parsers_map = {
            'list': list_parser,
            'rasters': list_rasters_parser,
            'detectors': list_detectors_parser
        }

    def handle_command(self, options):
        super()
        if options.list == 'rasters':
            rasters = self.client.list_rasters(options.folder)
            if options.output == 'ids_only':
                for r in rasters:
                    print(r['id'])
            else:  # default json
                print(json.dumps(rasters))
        elif options.list == 'detectors':
            print(json.dumps(self.client.list_detectors()))
        else:
            raise InvalidOptionError(self.parsers_map['list'])
