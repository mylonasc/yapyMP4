
from .utils import _read_atoms_from_mp4, _read_table_or_header_data
from .mp4reader import MP4Atom , MP4Data
from .version import __version__ # created during deployment.

import os
__version__=os.environ['YAPY_MP4_VERSION']
