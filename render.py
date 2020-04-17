import logging
import os
import sys
import xml.etree.ElementTree as ET
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import FLIP_TOP_BOTTOM

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def display_network(net: sumolib.net.Net, stats: ET.ElementTree, centre, args, max_size: int):
    """
    :param net: the network to display noisemap for
    :param stats: the stats file describing the network
    :param max_size: maximum width/height of the resulting image
    :return:
    """
    # Basics about the city and its size
    boundary = net.getBoundary()
    city_size = (boundary[2], boundary[3])

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

    # Load pretty font FIXME: find more ubiquitous default pretty font and maybe try for both Linux and Win
    try:
        font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationMono-Regular.ttf", size=12)
    except IOError:
        font = ImageFont.load_default()

    # Make image and prepare for drawing
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    COLOUR_CITY_GATE = (255, 0, 0)
    COLOUR_BUS_STOP = (250, 146, 0)
    COLOUR_SCHOOL = (255, 0, 216)
    COLOUR_CENTRE = (255, 0, 0, 128)

    # Draw streets
    if stats.find("streets") is not None:
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
    else:
        logging.warning(f"[render] Could not find any streets in statistics")

    # Draw city gates
    if stats.find("cityGates") is not None:
        for gate_xml in stats.find("cityGates").findall("entrance"):
            edge = net.getEdge(gate_xml.attrib["edge"])
            traffic = max(float(gate_xml.attrib["incoming"]), float(gate_xml.attrib["outgoing"]))
            x, y = position_on_edge(edge, float(gate_xml.attrib["pos"]))
            x *= width_scale
            y *= height_scale
            r = int(2 + traffic / 1.3)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 0))
    else:
        logging.warning(f"[render] Could not find any city-gates in statistics")

    # Draw bus stops
    if stats.find("busStations") is not None:
        for stop_xml in stats.find("busStations").findall("busStation"):
            edge = net.getEdge(stop_xml.attrib["edge"])
            x, y = position_on_edge(edge, float(stop_xml.attrib["pos"]))
            x *= width_scale
            y *= height_scale
            r = 2
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(250, 146, 0))
    else:
        logging.warning(f"[render] Could not find any bus-stations in statistics")

    # Draw schools
    if stats.find("schools") is not None:
        for school_xml in stats.find("schools").findall("school"):
            edge = net.getEdge(school_xml.attrib["edge"])
            capacity = int(school_xml.get('capacity'))
            x, y = position_on_edge(edge, float(school_xml.get('pos')))
            x *= width_scale
            y *= height_scale
            r = int(2 + capacity / 175)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 0, 216))
    else:
        logging.warning(f"[render] Could not find any schools in statistics")

    if not any([stats.find(x) for x in {"streets", "cityGates", "busStations", "schools"}]):
        logging.error("[render] No elements found in statistics, cannot display network and features")
        exit(1)

    # Flip image on the horizontal axis and update draw-pointer
    img = img.transpose(FLIP_TOP_BOTTOM)
    draw = ImageDraw.Draw(img, "RGBA")

    # Draw network name
    draw.text((2, 2), args['--net-file'], fill="#000000", font=font)

    Legend(max_size, height, draw, font) \
        .draw_distance_legend(city_size, width_scale) \
        .draw_gradient(((0, 255, 0), (0, 0, 255)), "Pop, work gradient") \
        .draw_legend(COLOUR_CENTRE, "Centre") \
        .draw_legend(COLOUR_SCHOOL, "School") \
        .draw_legend(COLOUR_BUS_STOP, "Bus stop") \
        .draw_legend(COLOUR_CITY_GATE, "City gate")

    img.show()


class Legend:
    def __init__(self, scale, height, draw, font):
        self.offset = 0
        self.scale = scale / 800
        self.r_box = 10 * self.scale
        self.icon_height = height - self.r_box - 10
        self.draw: ImageDraw.ImageDraw = draw
        self.font = font

    def draw_legend(self, colour, text):
        # Draw box and icon from beginning of offset
        x_icon, y_icon = self.offset, self.icon_height
        self.draw.rectangle((x_icon, y_icon, x_icon + self.r_box, y_icon + self.r_box), "#ffffff", "#000000")

        x_box_centre, y_box_centre = x_icon + self.r_box // 2, y_icon + self.r_box // 2

        r_icon = 4 * self.scale
        self.draw.ellipse((x_box_centre - r_icon, y_box_centre - r_icon, x_box_centre + r_icon, y_box_centre + r_icon),
                          colour)

        # offset by text-width
        self.draw.text((self.offset + self.r_box + 5, self.icon_height), text, "#000000", font=self.font)
        # Update offset
        self.offset += self.font.getsize(text=text)[0] + self.r_box * 2

        # Return self to allow chaining
        return self

    def draw_gradient(self, colour: Tuple[Tuple[int, int, int], Tuple[int, int, int]], text):
        # Define box dimensions
        h_box = int(1.2 * self.r_box)
        w_box = h_box * 2

        # draw box
        self.draw.rectangle((self.offset, self.icon_height, self.offset + w_box, self.icon_height + h_box),
                            "#ffffff", "#000000")

        # for element-wise operation on tuples
        import operator

        for i in range(1, w_box):
            # calculate left and right colour proportions
            ratio = i / w_box
            left = tuple(map(operator.mul, colour[1], (ratio, ratio, ratio)))
            inv_ratio = 1 - ratio
            right = tuple(map(operator.mul, colour[0], (inv_ratio, inv_ratio, inv_ratio)))
            # add colour proportions and write line in gradient
            line_colour = tuple(map(int, map(operator.add, left, right)))
            self.write_gradient_line(self.offset + i, self.icon_height, h_box, line_colour)

        # draw text
        self.draw.text((self.offset + w_box + 5, self.icon_height), text, "#000000", font=self.font)

        self.offset += self.font.getsize(text=text)[0] + w_box + 15
        return self

    def write_gradient_line(self, x, y, h, colour):
        for i in range(1, h):
            # put alpha level depending on height of line being drawn
            colour = colour[:3] + (int((1 - (i / h)) * 255),)
            self.draw.point((x, y + i), colour)

    def draw_distance_legend(self, city_size, width_scale):
        # Draw distance legend
        meters = find_dist_legend_size(max(city_size))
        self.offset += int(meters * width_scale)
        line_height = self.icon_height + self.r_box // 2

        # line
        self.draw.line([2, line_height, 2 + self.offset, line_height], (0, 0, 0), 1)
        # ticks
        self.draw.line([2, line_height + 5, 2, line_height - 5], (0, 0, 0), 1)
        self.draw.line([2 + self.offset, line_height + 5, 2 + self.offset, line_height - 5], (0, 0, 0), 1)

        self.draw.text([6, self.icon_height - 18], f"{meters} m", (0, 0, 0), font=self.font)
        # add padding
        self.offset += 10
        return self


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
