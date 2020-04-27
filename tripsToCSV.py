"""
Usage:
    tripsToCSV.py --net-file=FILE --trips-file=FILE [--display]

Input Options:
    -n, --net-file FILE         Input road network
    -s, --trips-file FILE       Input trips file
"""

import os
import sys
import csv
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw
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

# Info about net size and edges
offset_x, offset_y, xmax, ymax = net.getBoundary()
net_width, net_height = xmax - offset_x, ymax - offset_y
edge_count = len(net.getEdges())

# base of file name, e.g. "vejen.trips.rou.xml" -> "vejen"
fname = os.path.splitext(os.path.splitext(os.path.splitext(os.path.basename(args["--trips-file"]))[0])[0])[0]

starts = []
ends = []

with open(os.path.dirname(args["--trips-file"]) + f"/{fname}-trip-starts.csv", "w", newline="") as csv_starts:
    with open(os.path.dirname(args["--trips-file"]) + f"/{fname}-trip-ends.csv", "w", newline="") as csv_ends:
        writer_starts = csv.writer(csv_starts)
        writer_ends = csv.writer(csv_ends)

        next_print = 0.1 * edge_count
        progress = 0
        for edge in net.getEdges():

            # Find all trips that starts and ends on this edge and save the position along the edge
            trip_starts = [float(trip.attrib["arrivalPos"]) for trip in trips.findall("trip") if trip.attrib["from"] == edge.getID()]
            trip_ends = [float(trip.attrib["departPos"]) for trip in trips.findall("trip") if trip.attrib["to"] == edge.getID()]

            # Add trip start data points
            for start in trip_starts:
                x, y = position_on_edge(edge, start)
                x -= offset_x
                y -= offset_y
                start = (x, y)
                writer_starts.writerow(start)
                starts.append(start)

            # Add trip end data points
            for end in trip_ends:
                x, y = position_on_edge(edge, end)
                x -= offset_x
                y -= offset_y
                end = (x, y)
                writer_starts.writerow(end)
                ends.append(end)

            # Print a . whenever another 10% is done
            progress += 1
            if progress > next_print:
                next_print += 0.1 * edge_count
                print(".", end="")

# Display the start and end positions
if args["--display"]:
    # Calculate dimensions and scaling
    max_size = 800
    width_height_relation = net_height / net_width
    if net_width > net_height:
        width = max_size
        height = int(max_size * width_height_relation)
    else:
        width = int(max_size / width_height_relation)
        height = max_size
    width_scale = width / net_width
    height_scale = height / net_height

    # Render start points
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    for point in starts:
        x, y = point
        x *= width_scale
        y = (net_height - y) * height_scale
        color = (0, 200, 0)
        r = 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.show()

    # Render end points
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    for point in ends:
        x, y = point
        x *= width_scale
        y = (net_height - y) * height_scale
        color = (0, 0, 200)
        r = 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.show()
