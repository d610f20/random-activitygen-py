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

from Perlin import apply_perlin_noise, get_perlin_noise, get_edge_pair_centroid

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
    assert gate_count >= 0, "Number of city gates cannot be negative"
    # Find existing gates to determine how many we need to insert
    xml_gates = stats.find("cityGates")
    xml_entrances = xml_gates.findall("entrance")
    n = gate_count - len(xml_entrances)
    if n < 0:
        print(f"Warning: {gate_count} city gate was requested, but there are already {len(xml_entrances)} defined")
    if n <= 0:
        return
    print(f"Inserting {n} new city gates")

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


def random_school_edge(net: sumolib.net.Net, num_schools):
    edges = net.getEdges()

    # Sort all edges based on their avg coord
    edges.sort(key=lambda x: np.mean(get_edge_pair_centroid(x.getShape())))

    # Split edges into districts
    district_size = int(len(edges) / num_schools)
    districts = [edges[x:x + district_size] for x in range(0, len(edges), district_size)]

    # Pick out the one edge with highest perlin noise from each district and return these
    school_edges = []
    for district in districts:
        district.sort(key=lambda x: get_perlin_noise(get_edge_pair_centroid(x.getShape())[0],
                                                     get_edge_pair_centroid(x.getShape())[1]))
        school_edges.append(district[-1])

    print(school_edges)
    return school_edges


def setup_schools(net: sumolib.net.Net, stats: ET.ElementTree):
    # Voodoo parameter, seems to be about the value for a couple of danish cities.
    # In general one high school, per 5000-7000 inhabitant in a city
    inhabitants_per_school = 5000

    school_opening_earliest = 7 * 3600
    school_opening_latest = 10 * 3600
    school_closing_earliest = 13 * 3600
    school_closing_latest = 17 * 3600
    stepsize = int(0.25 * 3600)

    # Find number of schools to be inserted on edges
    xml_general = stats.find('general')
    inhabitants = xml_general.get('inhabitants')
    num_schools = math.ceil(int(inhabitants) / inhabitants_per_school)

    # Creates a list of school start times, in seconds. Ranges from 7am to 10am, with 15min intervals
    school_start_times = list(range(school_opening_earliest, school_opening_latest, stepsize))

    # Creates a list of school end times, in seconds. Ranges from 13pm to 17pm, with 15min intervals
    school_end_times = list(range(school_closing_earliest, school_closing_latest, stepsize))

    # Find edges to place schools on
    xml_schools = stats.find('schools')
    school_edges = random_school_edge(net, num_schools)

    # Insert schools, with random parameters
    print("Inserting " + str(len(school_edges)) + " new schools")
    for index in school_edges:
        school: sumolib.net.edge.Edge = index
        begin_age = random.choice(list(range(0, 19)))
        end_age = random.choice(list(range(begin_age + 1, 26)))

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school.getID()),
            "pos": str(random.randint(0, 100)),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(100, 500)),
            "opening": str(random.choice(school_start_times)),
            "closing": str(random.choice(school_end_times))
        })


if __name__ == "__main__":
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    # Read in SUMO network
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    stats = ET.parse(args["--stat-file"])

    apply_perlin_noise(net, stats)
    setup_city_gates(net, stats, int(args["--gates.count"]))

    setup_schools(net, stats)

    # Write statistics back
    stats.write(args["--output-file"])
