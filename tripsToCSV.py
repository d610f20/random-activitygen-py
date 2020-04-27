"""
Usage:
    tripsToCSV.py --net-file=FILE --trips-file=FILE

Input Options:
    -n, --net-file FILE         Input road network
    -s, --trips-file FILE       Input trips file
"""

import os
import sys
import csv
import xml.etree.ElementTree as ET

from docopt import docopt

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


args = docopt(__doc__)

# Read input files
net = sumolib.net.readNet(args["--net-file"])
trips = ET.parse(args["--trips-file"])

offset_x, offset_y, xmax, ymax = net.getBoundary()
width, height = xmax - offset_x, ymax - offset_y
edge_count = len(net.getEdges())

fname = os.path.splitext(os.path.splitext(os.path.splitext(os.path.basename(args["--trips-file"]))[0])[0])[0]

with open(os.path.dirname(args["--trips-file"]) + f"/{fname}-trip-starts.csv", "w", newline="") as csv_starts:
    with open(os.path.dirname(args["--trips-file"]) + f"/{fname}-trip-ends.csv", "w", newline="") as csv_ends:
        writer_starts = csv.writer(csv_starts)
        writer_ends = csv.writer(csv_ends)

        next_print = 0.1 * edge_count
        progress = 0
        for edge in net.getEdges():

            tripStarts = len([trip for trip in trips.findall("trip") if trip.attrib["from"] == edge.getID()])
            tripEnds = len([trip for trip in trips.findall("trip") if trip.attrib["to"] == edge.getID()])

            x, y = position_on_edge(edge, edge.getLength() / 2)
            x -= offset_x
            y -= offset_y

            writer_starts.writerow([x, y, tripStarts])
            writer_ends.writerow([x, y, tripEnds])

            progress += 1
            if progress > next_print:
                next_print += 0.1 * edge_count
                print(".", end="")
