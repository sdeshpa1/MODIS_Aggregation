"""Top-level package for MODIS."""

__author__ = """Sukhada Deshpande"""
__email__ = 'sdeshpa1@umbc.edu'
__version__ = '0.1.0'


from .cloud_fraction_aggregate import *


# if somebody does "from Sample import *", this is what they will
# be able to access:
__all__ = [
    'aggregateOneFileData'
    , 'getInputDirectories'
    , 'calculateCloudFraction'
    ,'displayOutput'
]
