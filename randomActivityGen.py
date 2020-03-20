"""
Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--gates.count=N]

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    --gates.count N             Number of city gates in the city [default: 4]
    -h, --help                  Show this screen.
    --version                   Show version.
"""
import math
import os
import random
import sys
import xml.etree.ElementTree as ET
from typing import Tuple

import numpy as np
from docopt import docopt

from Perlin import apply_perlin_noise

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_city_centre(net: sumolib.net.Net) -> Tuple[float, float]:
    """
    Finds the city centre; average node coord of all nodes in the net
    """
    node_coords = [node.getCoord() for node in net.getNodes()]
    return float(np.mean([c[0] for c in node_coords])), float(np.mean([c[1] for c in node_coords]))


def setup_city_gates(net: sumolib.net.Net, stats: ET.ElementTree, gate_count: int):
    # Find existing gates to determine how many we need to insert
    xml_gates = stats.find("cityGates")
    xml_entrances = xml_gates.findall("entrance")
    n = gate_count - len(xml_entrances)
    print(xml_gates, [e.get("edge") for e in xml_entrances])
    print(f"Inserting {n} city gates")

    # Finds all nodes that are dead ends, i.e. nodes that only have one neighbouring node
    dead_ends = [n for n in net.getNodes() if len(n.getNeighboringNodes()) == 1]

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

    for dir in dirs:
        # Find the dead ends furthest in each direction using the dot product and argmax. Those nodes will be our gates.
        # Duplicates are possible and no problem. That just means there will be more traffic through that gate.
        gate_index = int(np.argmax([np.dot(node.getCoord(), dir) for node in dead_ends]))
        gate = dead_ends[gate_index]

        # Decide proportion of the incoming and outgoing vehicles coming through this gate
        # These numbers are relatively to the values of the other gates
        incoming = 1 + random.random()
        outgoing = 1 + random.random()

        # Add entrance to stats file
        edge = gate.getOutgoing()[0]
        ET.SubElement(xml_gates, "entrance", attrib={
            "edge": edge.getID(),
            "incoming": str(incoming),
            "outgoing": str(outgoing),
            "pos": "0"
        })


if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    # Read in SUMO network
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    stats = ET.parse(args["--stat-file"])

    apply_perlin_noise(net, stats)
    setup_city_gates(net, stats, int(args["--gates.count"]))

    # Write statistics back
    stats.write(args["--output-file"])
