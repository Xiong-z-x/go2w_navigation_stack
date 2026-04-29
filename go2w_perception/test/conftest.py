import sys
from pathlib import Path


PACKAGE_SOURCE = Path(__file__).resolve().parents[1]
if str(PACKAGE_SOURCE) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SOURCE))
