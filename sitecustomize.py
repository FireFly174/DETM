"""Project-wide site customisation to avoid name clashes with stdlib modules."""

import sys

# Move the working directory entry to the end so stdlib modules (e.g. ``logging``)
# are resolved before similarly named local packages.
if "" in sys.path:
    sys.path.remove("")
    sys.path.append("")
