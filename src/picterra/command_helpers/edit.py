from ..helpers import InvalidOptionError, CommandParser


class EditCommandParser(CommandParser):
    def __init__(self, parser, logger):
        super().__init__('edit', parser, logger)
        edit_parser = self.parser.add_parser('edit', help="Edit resources")
        edit_subparsers = edit_parser.add_subparsers(dest='edit')
        ## Edit raster
        edit_raster_parser = edit_subparsers.add_parser('raster', help="Edits a raster")
        edit_raster_parser.add_argument("raster", help="ID of the raster to edit", type=str)
        edit_raster_parser.add_argument(
            "--name", help="Name to give to the raster", type=str, required=False)
        self.parsers_map = {
            'edit': edit_parser,
            'raster': edit_raster_parser
        }

    def handle_command(self, options):
        super()
        if options.edit == 'raster':
            self.client.edit_raster(options.raster, name=options.name)
            self.logger.info('Edited raster whose id is %s' % options.raster)
        else:
            raise InvalidOptionError(self.parsers_map['edit'])
