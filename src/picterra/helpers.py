from argparse import ArgumentParser, Namespace
from typing import Dict
import sys
from logging import Logger
from .client import APIClient, APIError

class InvalidOptionError(Exception):
    """TODO"""
    def __init__(self, parser: ArgumentParser):            
        super().__init__('Invalid option error')
        self.parser = parser

ParserMap = Dict[str, ArgumentParser]

class CommandParser():
    """TODO"""
    def __init__(self, name: str, parser: ArgumentParser, logger: Logger):  
        """TODO"""          
        self.name = name
        self.parser = parser
        self.logger = logger
        self.parsers_map = None
        try:
            self.client = APIClient()
        except APIError as e:
            sys.exit("\033[91m%s\033[00m" % e)

    def handle_command(self, options: Namespace):
        """TODO"""
        if not self.client:
            self.parser.print_help()
