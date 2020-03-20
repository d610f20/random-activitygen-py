"""
Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    -h, --help                  Show this screen.
    --version                   Show version.
"""
import os
import sys

from docopt import docopt
import xml.etree.ElementTree as ET

from Perlin import apply_perlin_noise

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib

if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen v0.1")
    # Read in SUMO network
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    stats = ET.parse(args["--stat-file"])

    apply_perlin_noise(net, stats)

    # Write statistics back
    stats.write(args["--output-file"])
