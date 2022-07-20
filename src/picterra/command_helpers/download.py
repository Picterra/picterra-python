from ..helpers import InvalidOptionError, CommandParser


class DownloadCommandParser(CommandParser):
    def __init__(self, parser, logger):
        super().__init__('download', parser, logger)
        download_parser = self.parser.add_parser('download', help="Download resources")
        download_subparsers = download_parser.add_subparsers(dest='download')
        ## Download raster
        download_raster_parser = download_subparsers.add_parser('raster', help="Downloads a raster")
        download_raster_parser.add_argument("raster", help="ID of the raster to download", type=str)
        download_raster_parser.add_argument(
            "path", help="Path to the local file where the raster will be saved", type=str)
        self.parsers_map = {
            'download': download_parser,
            'raster': download_raster_parser
        }

    def handle_command(self, options):
        super()
        if options.download == 'raster':
            self.client.download_raster_to_file(options.raster, options.path)
            self.logger.info('Downloaded raster whose id is %s' % options.raster)
        else:
            raise InvalidOptionError(self.parsers_map['download'])
