import os
import sys

import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import FLIP_TOP_BOTTOM

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def display_network(net: sumolib.net.Net, stats: ET.ElementTree, centre, args, max_width: int, max_height: int):
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

    # Load pretty font FIXME: find more ubiquitous default pretty font and maybe try for both Linux and Win
    try:
        font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationMono-Regular.ttf", size=12)
    except IOError:
        font = ImageFont.load_default()

    # Make image and prepare for drawing
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")

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

    # Draw centre
    x, y = int(centre[0]) * width_scale, int(centre[1]) * height_scale
    r = 15
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0, 128))

    # Flip image on the horizontal axis and update draw-pointer
    img = img.transpose(FLIP_TOP_BOTTOM)
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw network name
    draw.text((2, 2), args['--net-file'], fill="#000000", font=font)

    # Draw distance legend
    meters = find_dist_legend_size(max(city_size))
    pixels = int(meters * width_scale)
    draw.line([2, height - 3, 2 + pixels, height - 3], (0, 0, 0), 1)
    draw.line([2, height, 2, height - 5], (0, 0, 0), 1)
    draw.line([2 + pixels, height, 2 + pixels, height - 5], (0, 0, 0), 1)
    draw.text([6, height - 18], f"{meters} m", (0, 0, 0), font=font)

    # Draw colour legend
    legend_offset = pixels + 15

    class Legend:
        offset = legend_offset
        text_height = height - 15
        icon_height = height - 9

        def __init__(self, offset):
            text = "Legend:"
            draw.text((offset, self.text_height), text=text, fill=(0, 0, 0), font=font)
            self.offset += font.getsize(text)[0] + 10

        def draw_icon(self, colour, text):
            # Draw box and icon from beginning of offset
            x_icon, y_icon = self.offset, self.icon_height
            r_box = 5
            draw.rectangle((x_icon - r_box, y_icon - r_box, x_icon + r_box, y_icon + r_box), "#ffffff", "#000000")

            r_icon = 2
            draw.ellipse((x_icon - r_icon, y_icon - r_icon, x_icon + r_icon, y_icon + r_icon), colour)

            # offset by text-width
            draw.text((self.offset + 10, self.text_height), text, (0, 0, 0), font=font)
            # Update offset
            self.offset += font.getsize(text=text)[0] + 20

            # Return self to allow chaining
            return self

    Legend(legend_offset) \
        .draw_icon("green", "test") \
        .draw_icon("blue", "testtesttest") \
        .draw_icon("red", "testtest")

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
