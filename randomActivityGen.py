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
from typing import Tuple

import numpy as np
from docopt import docopt

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

import sumolib


def find_city_centre(net: sumolib.net.Net) -> Tuple[float, float]:
    """
    Finds the city centre; average node coord of all nodes in the net
    """
    node_coords = [node.getCoord() for node in net.getNodes()]
    return float(np.mean([c[0] for c in node_coords])), float(np.mean([c[1] for c in node_coords]))


if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen 0.1")

    net = sumolib.net.readNet(args["--net-file"])

    centre = find_city_centre(net)
    print(f"City centre: {centre}")

