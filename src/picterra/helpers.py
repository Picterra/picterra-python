from argparse import ArgumentParser, ArgumentTypeError
from typing import Union

class InvalidOptionError(Exception):
    """Exception carrying a parser"""
    def __init__(self, parser: ArgumentParser):            
        super().__init__('Invalid option error')
        self.parser = parser


def range_limited_type(min: Union[int, float], max: Union[int, float]):
    """
    Return function handle of an argument type function for
       ArgumentParser checking a float/int range: mini <= arg <= maxi
         mini - minimum acceptable argument
         maxi - maximum acceptable argument
    """

    # Define the function with default arguments
    def range_limited_type_checker(arg):
        """ Type function for argparse - a number within some predefined bounds """
        typ = type(min)
        try:
            v = typ(arg)
        except ValueError:
            raise ArgumentTypeError("Must be " + str(typ))
        if v < min or v > max:
            raise ArgumentTypeError("Argument must be < " + str(min) + "and > " + str(max))
        return arg

    # Return function handle to checking function
    return range_limited_type_checker
