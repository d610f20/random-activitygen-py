import logging
import os
import sys

import xml.etree.ElementTree as ET
from typing import Tuple

from PIL import Image, ImageDraw
from PIL.Image import FLIP_TOP_BOTTOM

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def display_network(net: sumolib.net.Net, stats: ET.ElementTree, max_size: int):
    """
    :param net: the network to display noisemap for
    :param stats: the stats file describing the network
    :param max_size: maximum width/height of the resulting image
    :return:
    """
    # Basics about the city and its size
    boundary = net.getBoundary()
    city_size = (boundary[2] - boundary[0], boundary[3] - boundary[1])

    # Determine the size of the picture and scalars for scaling the city to the correct size
    # We might have a very wide city. In this case we want to produce a wide image
    width_height_relation = city_size[1] / city_size[0]
    if city_size[0] > city_size[1]:
        width = max_size
        height = int(max_size * width_height_relation)
    else:
        width = int(max_size * width_height_relation)
        height = max_size
    width_scale = width / city_size[0]
    height_scale = height / city_size[1]

    def to_png_space(xy: Tuple[float, float]) -> Tuple[float, float]:
        """ Translate the given city position to a png position """
        return (xy[0] - boundary[0]) * width_scale, (xy[1] - boundary[1]) * height_scale

    # Make image and prepare for drawing
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw streets
    if stats.find("streets") is not None:
        for street_xml in stats.find("streets").findall("street"):
            edge = net.getEdge(street_xml.attrib["edge"])
            population = float(street_xml.attrib["population"])
            industry = float(street_xml.attrib["workPosition"])
            from_pos = to_png_space(edge.getFromNode().getCoord())
            to_pos = to_png_space(edge.getToNode().getCoord())
            green = int(35 + 220 * (1 - industry))
            blue = int(35 + 220 * (1 - population))
            draw.line((from_pos, to_pos), (0, green, blue), int(1.5 + 3.5 * population ** 1.5))
    else:
        logging.warning(f"[render] Could not find any streets in statistics")

    # Draw city gates
    if stats.find("cityGates") is not None:
        for gate_xml in stats.find("cityGates").findall("entrance"):
            edge = net.getEdge(gate_xml.attrib["edge"])
            traffic = max(float(gate_xml.attrib["incoming"]), float(gate_xml.attrib["outgoing"]))
            x, y = to_png_space(position_on_edge(edge, float(gate_xml.attrib["pos"])))
            r = int(2 + traffic / 1.3)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0))
    else:
        logging.warning(f"[render] Could not find any city-gates in statistics")

    # Draw bus stops
    if stats.find("busStations") is not None:
        for stop_xml in stats.find("busStations").findall("busStation"):
            edge = net.getEdge(stop_xml.attrib["edge"])
            x, y = to_png_space(position_on_edge(edge, float(stop_xml.attrib["pos"])))
            r = 2
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(250, 146, 0))
    else:
        logging.warning(f"[render] Could not find any bus-stations in statistics")

    # Draw schools
    if stats.find("schools") is not None:
        for school_xml in stats.find("schools").findall("school"):
            edge = net.getEdge(school_xml.attrib["edge"])
            capacity = int(school_xml.get('capacity'))
            x, y = to_png_space(position_on_edge(edge, float(school_xml.get('pos'))))
            r = int(2 + capacity / 175)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 216))
    else:
        logging.warning(f"[render] Could not find any schools in statistics")

    if not any([stats.find(x) for x in {"streets", "cityGates", "busStations", "schools"}]):
        logging.error("[render] No elements found in statistics, cannot display network and features")
        exit(1)

    # Flip image on the horizontal axis and update draw-pointer
    img = img.transpose(FLIP_TOP_BOTTOM)
    draw = ImageDraw.Draw(img)

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
