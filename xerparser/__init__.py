"""Project File Parser Package - Parses project management files using MPXJ

Supports: XER, MPP, MPX, XML, PMXML, PP, and many more formats.
"""

__version__ = "2.0.0"
__author__ = "XER Parser"

from .src.parser import file_reader, parser, XerFile, is_supported_file

__all__ = ["file_reader", "parser", "XerFile", "is_supported_file"]
