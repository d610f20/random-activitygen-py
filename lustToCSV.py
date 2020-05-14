import csv
import datetime
import os
import random
import sys
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from matplotlib.ticker import FuncFormatter, MultipleLocator

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


net = sumolib.net.readNet("in/lust/lust.net.xml")
# Info about net size and edges
offset_x, offset_y, xmax, ymax = net.getBoundary()
net_width, net_height = xmax - offset_x, ymax - offset_y
edge_count = len(net.getEdges())
print("Loaded network")

# ======================== EXTRACT DATA ========================

data = []


def extract_trips_from_routes_file(route_file):
    xml = ET.parse(route_file)
    for vehicle in xml.findall("vehicle"):
        departTime = float(vehicle.get("depart"))
        edge_id = vehicle.find("route").get("edges").split(" ")[0]
        edge = net.getEdge(edge_id)
        x, y = position_on_edge(edge, edge.getLength() * random.random())
        data.append((x, y, departTime))


def extract_trips_from_flow_file(flow_file):
    xml = ET.parse(flow_file)
    for flow in xml.findall("flow"):
        begin = int(float(flow.get("begin")))
        end = int(float(flow.get("end")))
        period = int(float(flow.get("period")))
        edge_id = flow.get("from")
        edge = net.getEdge(edge_id)
        edge_length = edge.getLength()
        for t in range(begin, end, period):
            x, y = position_on_edge(edge, edge_length * random.random())
            data.append((x, y, t))


extract_trips_from_routes_file("in/lust/local.0.rou.xml")
print(len(data), "trips extracted")
extract_trips_from_routes_file("in/lust/local.1.rou.xml")
print(len(data), "trips extracted")
extract_trips_from_routes_file("in/lust/local.2.rou.xml")
print(len(data), "trips extracted")

# ======================== WRITE DATA =========================

with open("out/lust/lust-trip-starts.csv", "w", newline="") as csv_starts:
    writer_starts = csv.writer(csv_starts)
    for datapoint in data:
        writer_starts.writerow(datapoint)

print("Finished writing data")

# ======================= RENDERING ========================

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

# PNGS
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
    r = 1
    draw.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 140))
    if 23000 < z < 33000:
        # Early rush hour
        drawBefore12.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 140))
        before += 1
    if 58000 < z < 73000:
        # Late rush hour
        drawAfter12.ellipse([x - r, y - r, x + r, y + r], fill=(0, 0, 0, 140))
        after += 1

img.save(f"out/lust/lust-trips.png")
imgBefore12.save(f"out/lust/lust-trips-early-rush-hour.png")
imgAfter12.save(f"out/lust/lust-trips-late-rush-hour.png")

# GIF
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
    draw.text((10, 10), f"{datetime.timedelta(seconds=timeslot)} ({timeslot})", fill=(0, 0, 0))
    draw.line([0, 1, width * timeslot / 86400, 1], fill=(0, 0, 0))
    images.append(img)

images[0].save(f"out/lust/lust-trips.gif", save_all=True, append_images=images[1:], optimize=False, duration=8, loop=0)

# Histogram
time_data = [datapoint[2] for datapoint in data]

fig, ax = plt.subplots(1, 1)
bins = ax.hist(time_data, bins=86400 // (60 * 10))
ax.xaxis.set_major_locator(MultipleLocator(3600 * 4))
ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int((x - x % 3600)/3600)}:00"))
plt.show()
