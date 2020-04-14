import os
import sys

import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

from perlin import get_edge_pair_centroid
from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def display_network(net: sumolib.net.Net, stats: ET.ElementTree, max_width: int, max_height: int):
    """
    :param net: the network to display noisemap for
    :param stats: the stats file describing the network
    :param max_width: maximum width of the resulting image
    :param max_height: maximum width of the resulting image
    :return:
    """
    # Basics about the city and its size
    boundary = net.getBoundary()
    city_size = (boundary[2], boundary[3])

    # Determine the size of the picture and scalars for scaling the city to the correct size
    # We might have a very wide city. In this case we want to produce a wide image
    width_height_relation = city_size[1] / city_size[0]
    width, height = (max_width, int(max_height * width_height_relation)) if city_size[0] > city_size[1] else (
        int(max_width / width_height_relation), max_height)
    width_scale = width / city_size[0]
    height_scale = height / city_size[1]

    # Make image and prepare for drawing
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw streets
    for street_xml in stats.find("streets").findall("street"):
        edge = net.getEdge(street_xml.attrib["edge"])
        population = float(street_xml.attrib["population"])
        industry = float(street_xml.attrib["workPosition"])
        x1, y1 = edge.getFromNode().getCoord()
        x2, y2 = edge.getToNode().getCoord()
        green = int(255 * (1 - industry))
        blue = int(255 * (1 - population))
        coords = [x1 * width_scale, y1 * height_scale, x2 * width_scale, y2 * height_scale]
        draw.line(coords, (0, green, blue), int(0.5 + population * 5))

    # Draw city gates
    for gate_xml in stats.find("cityGates").findall("entrance"):
        edge = net.getEdge(gate_xml.attrib["edge"])
        traffic = max(float(gate_xml.attrib["incoming"]), float(gate_xml.attrib["outgoing"]))
        x, y = position_on_edge(edge, float(gate_xml.attrib["pos"]))
        x *= width_scale
        y *= height_scale
        r = int(2 + traffic / 1.3)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0))

    # Draw bus stops
    for stop_xml in stats.find("busStations").findall("busStation"):
        edge = net.getEdge(stop_xml.attrib["edge"])
        x, y = position_on_edge(edge, float(stop_xml.attrib["pos"]))
        x *= width_scale
        y *= height_scale
        r = 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(250, 146, 0))

    # Draw schools
    for school_xml in stats.find("schools").findall("school"):
        edge = net.getEdge(school_xml.attrib["edge"])
        capacity = int(school_xml.get('capacity'))
        x, y = position_on_edge(edge, float(school_xml.get('pos')))
        x *= width_scale
        y *= height_scale
        r = int(2 + capacity / 175)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 216))

    # Draw distance legend
    meters = find_dist_legend_size(max(city_size))
    pixels = int(meters * width_scale)
    draw.line([2, height - 3, 2 + pixels, height - 3], (0, 0, 0), 1)
    draw.line([2, height, 2, height - 5], (0, 0, 0), 1)
    draw.line([2 + pixels, height, 2 + pixels, height - 5], (0, 0, 0), 1)
    draw.text([6, height - 18], f"{meters} m", (0, 0, 0))

    img.show()


def find_dist_legend_size(real_size, frac: float = 0.2):
    """
    Returns a nice number that closely matches the fraction of the real size
    """
    # A "nice number" is a number equal to s * 10^n where n is an integer and s is one of the scales from this list:
    scales = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.5]
    # Iterate n until the nice number is greater than real_size * frac
    meters = 10
    while meters < real_size * frac:
        for s in scales:
            if meters * s > real_size * frac:
                return int(meters * s)
        meters *= 10
    return meters
