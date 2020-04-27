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

offset_x, offset_y, xmax, ymax = net.getBoundary()
net_width, net_height = xmax - offset_x, ymax - offset_y
edge_count = len(net.getEdges())

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

            trip_starts = len([trip for trip in trips.findall("trip") if trip.attrib["from"] == edge.getID()])
            trip_ends = len([trip for trip in trips.findall("trip") if trip.attrib["to"] == edge.getID()])

            x, y = position_on_edge(edge, edge.getLength() / 2)
            x -= offset_x
            y -= offset_y

            start = (x, y, trip_starts)
            end = (x, y, trip_ends)

            writer_starts.writerow(start)
            writer_ends.writerow(end)

            starts.append(start)
            ends.append(end)

            progress += 1
            if progress > next_print:
                next_print += 0.1 * edge_count
                print(".", end="")

if args["--display"]:
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

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    for point in starts:
        x, y, c = point
        if c == 0:
            continue
        x *= width_scale
        y = (net_height - y) * height_scale
        color = (0, min(255, 40 * c), 0)
        r = 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.show()

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    for point in ends:
        x, y, c = point
        if c == 0:
            continue
        x *= width_scale
        y = (net_height - y) * height_scale
        color = (0, 0, min(255, 40 * c))
        r = 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    img.show()
