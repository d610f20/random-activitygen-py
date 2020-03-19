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
import math
import os
import random
import sys
from typing import Tuple, List

import numpy as np
from docopt import docopt
import xml.etree.ElementTree as ET

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



def setup_city_gates(net: sumolib.net.Net, stats: ET.ElementTree, gate_count: int):

    centre = find_city_centre(net)

    # Finds all nodes that are dead ends, i.e. nodes that only have one neighbouring node
    dead_ends = [n for n in net.getNodes() if len(n.getNeighboringNodes()) == 1]

    n = gate_count

    # Find n unit vectors pointing in different directions
    # If n = 4 and base_rad = 0 we get the cardinal directions:
    #      N
    #      |
    # W<---o--->E
    #      |
    #      S
    tau = math.pi * 2
    base_rad = random.random() * tau
    rads = [(base_rad + i * tau / n) % tau for i in range(0, n)]
    dirs = [(math.cos(rad), math.sin(rad)) for rad in rads]

    # Find the dead ends furthest in each direction using the dot product and argmax. Those nodes will be our gates
    gate_indexes = [np.argmax([np.dot(node.getCoord(), dir) for node in dead_ends]) for dir in dirs]
    # We store the gates in a set to avoid duplicates
    gates = {dead_ends[i] for i in gate_indexes}
    print({g.getID() for g in gates})
    pass


if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen 0.1")

    net = sumolib.net.readNet(args["--net-file"])

    setup_city_gates(net, None, 5)
