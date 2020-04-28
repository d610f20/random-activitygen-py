"""
Usage:
    tripsToCSV.py --net-file=FILE --trips-file=FILE [--gif]

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
fname = os.path.basename(args["--trips-file"])
while "." in fname:
    fname = os.path.splitext(fname)[0]

data = []
with open(os.path.dirname(args["--trips-file"]) + f"/{fname}-trip-starts.csv", "w", newline="") as csv_starts:
        writer_starts = csv.writer(csv_starts)

        next_print = 0.1 * edge_count
        progress = 0
        for edge in net.getEdges():

            # Find all trips that starts on this edge and save the position along the edge
            trip_starts = [(float(trip.attrib["departPos"]), float(trip.attrib["depart"])) for trip in trips.findall("trip") if trip.attrib["from"] == edge.getID()]

            # Add trip start data points
            for (departPos, departTime) in trip_starts:
                x, y = position_on_edge(edge, departPos)
                x -= offset_x
                y -= offset_y
                datapoint = (x, y, departTime)
                writer_starts.writerow(datapoint)
                data.append(datapoint)

            # Print a . whenever another 10% is done
            progress += 1
            if progress > next_print:
                next_print += 0.1 * edge_count
                print(".", end="")

# Display the start and end positions
if args["--gif"]:
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

    timeslot_size = 300
    buckets = [(timeslot, [datapoint for datapoint in data if timeslot < datapoint[2] < timeslot + timeslot_size * 3]) for timeslot in range(0, 86400, timeslot_size)]

    images = []
    for (timeslot, departures) in buckets:
        # Render start points
        img = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        for point in departures:
            x, y, z = point
            x *= width_scale
            y = (net_height - y) * height_scale
            r = 2
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0))
        draw.text((10, 10), f"t={timeslot}", fill=(0, 0, 0))
        draw.line([0, 1, width * timeslot / 84600, 1], fill=(0, 0, 0))
        images.append(img)

    images[0].save(f"out/cities/{fname}-trips.gif", save_all=True, append_images=images[1:], optimize=False, duration=10, loop=0)
