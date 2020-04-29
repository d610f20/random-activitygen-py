"""
Usage:
    tripsToCSV.py --net-file=FILE --trips-file=FILE [--png] [--gif]

Input Options:
    -n, --net-file FILE         Input road network
    -s, --trips-file FILE       Input trips file
"""

import os
import sys
import csv
import xml.etree.ElementTree as ET
import random

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

    for trip_xml in trips.findall("trip"):
        edge = net.getEdge(trip_xml.get("from"))
        departTime = float(trip_xml.get("depart"))
        departPos = float(trip_xml.get("departPos") or edge.getLength() * random.random())

        x, y = position_on_edge(edge, departPos)
        x -= offset_x
        y -= offset_y
        datapoint = (x, y, departTime)
        writer_starts.writerow(datapoint)
        data.append(datapoint)

if args["--png"] or args["--gif"]:
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

    if args["--png"]:
        img = Image.new("RGB", (width, height), (255, 255, 255))
        imgBefore12 = Image.new("RGB", (width, height), (255, 255, 255))
        imgAfter12 = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        drawBefore12 = ImageDraw.Draw(imgBefore12, "RGBA")
        drawAfter12 = ImageDraw.Draw(imgAfter12, "RGBA")
        before = 0
        after = 0
        for point in data:
            x, y, z = point
            x *= width_scale
            y = (net_height - y) * height_scale
            r = 2
            draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0))
            if z < 86400 / 2:
                drawBefore12.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0))
                before += 1
            if z >= 86400 / 2:
                drawAfter12.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0))
                after += 1

        img.save(f"out/cities/{fname}-trips.png")
        imgBefore12.save(f"out/cities/{fname}-trips-before12.png")
        imgAfter12.save(f"out/cities/{fname}-trips-after12.png")
        print(before, after)

    if args["--gif"]:
        timeslot_size = 300  # 5 minutes
        buckets = [(timeslot, [datapoint for datapoint in data if timeslot < datapoint[2] < timeslot + timeslot_size * 3]) for timeslot in range(0, 86400, timeslot_size)]

        images = []
        for (timeslot, departures) in buckets:
            img = Image.new("RGB", (width, height), (255, 255, 255))
            draw = ImageDraw.Draw(img, "RGBA")
            for point in departures:
                x, y, z = point
                x *= width_scale
                y = (net_height - y) * height_scale
                r = 2
                draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0))
            draw.text((10, 10), f"t={timeslot}", fill=(0, 0, 0))
            draw.line([0, 1, width * timeslot / 86400, 1], fill=(0, 0, 0))
            images.append(img)

        images[0].save(f"out/cities/{fname}-trips.gif", save_all=True, append_images=images[1:], optimize=False, duration=10, loop=0)
