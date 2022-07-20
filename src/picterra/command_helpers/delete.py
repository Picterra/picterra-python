from ..helpers import CommandParser, InvalidOptionError


class DeleteCommandParser(CommandParser):
    def __init__(self, parser, logger):            
        super().__init__('delete', parser, logger)
        delete_parser = self.parser.add_parser('delete', help="Delete resources")
        delete_subparsers = delete_parser.add_subparsers(dest='delete')
        ## Delete raster
        delete_raster_parser = delete_subparsers.add_parser('raster', help="Removes a raster")
        delete_raster_parser.add_argument("raster", help="ID of the raster to delete", type=str)
        ## Delete detector
        delete_detector_parser = delete_subparsers.add_parser('detector', help="Removes a detector")
        delete_detector_parser.add_argument("detector", help="ID of the detector to delete", type=str)
        ## Delete detection areas
        delete_detectionarea_parser = delete_subparsers.add_parser(
            "detection_area", help="Removes the detection areas of raster, if any")
        delete_detectionarea_parser.add_argument(
            "raster", help="ID of the raster whose detection areas will be deleted", type=str)
        self.parsers_map = {
            'delete': delete_parser,
            'raster': delete_raster_parser,
            'detector': delete_detector_parser,
            'detection_area': delete_detectionarea_parser
        }

    def handle_command(self, options):
        super()
        if options.delete == 'raster':
            self.client.delete_raster(options.raster)
            self.logger.info('Deleted raster whose id was %s' % options.raster)
        elif options.delete == 'detector':
            self.client.delete_detector(options.detector)
            self.logger.info('Deleted detector whose id was %s' % options.detector)
        elif options.delete == 'detection_area':
            self.logger.debug('Removing detection area from raster %s..' % options.raster)
            self.client.remove_raster_detection_areas(options.raster)
            self.logger.info('Removed detection area for raster whose id is %s' % options.raster)
        else:
            raise InvalidOptionError(self.parsers_map['delete'])
