import os
import sys
import xml.etree.ElementTree as ET
from pprint import pprint
from xml.etree import ElementTree
import random

from render import toimage

import noise
import numpy as np

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib

# The 'noise' lib has good resolution until above 10 mil, but a SIGSEGV is had on values above [-100000, 100000]
# FIXME: these values result in a noisemap which contains CRT-like lines and patterns. Find better, sane values.
# POPULATION_BASE = random.randrange(-1000, 1000)
POPULATION_BASE: float = 0.0005
# INDUSTRY_BASE = random.randrange(-1000, 1000)
INDUSTRY_BASE: float = 0


def get_edge_pair_centroid(coords: list) -> (float, float):
    """
    Centroid of rectangle (edge_pair) = (width/2, height/2)
    :param coords: [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)]
    :return: Centroid of given shape
    """
    x_avg = np.mean([pos[0] for pos in coords])
    y_avg = np.mean([pos[1] for pos in coords])
    return x_avg, y_avg


def get_perlin_noise(x: float, y: float, base: float, scale: float, octaves: int) -> float:
    """
    The 'noise' lib returns a value in the range of [-1:1]. The noise value is scaled to the range of [0:1].
    :param base: offset into noisemap
    :param x: the sample point for x
    :param y: the sample point for y
    :return: a normalised float of the sample in noisemap
    """
    return (noise.pnoise2(x=x * scale, y=y * scale, octaves=octaves, base=base) + 1) / 2


def get_population_number(edge: sumolib.net.edge.Edge, base: float, scale: float, octaves: int, centre, radius) -> float:
    """
    Returns a Perlin simplex noise at centre of given street
    :param base: offset into noisemap
    :param edge: the edge
    :param centre:
    :param radius:
    :return: the scaled noise value as float in [0:1]
    """
    x, y = get_edge_pair_centroid(edge.getShape())
    return get_perlin_noise(x=float(x), y=float(y), base=base, scale=scale, octaves=octaves) + (
            1 - (distance((x, y), centre) / radius))


def apply_network_noise(net: sumolib.net.Net, xml: ElementTree, scale: float, octaves: int):
    """
    Calculate and apply Perlin noise in [0:1] range for each street for population and industry
    :param net: the SUMO network
    :param xml: the statistics XML for the network
    :return:
    """
    # Calculate and apply Perlin noise for all edges in network to population in statistics
    print("Writing Perlin noise to population and industry")

    from randomActivityGen import find_city_centre
    centre = find_city_centre(net)
    radius = radius_of_network(net, centre)

    streets = xml.find("streets")
    if streets is None:
        streets = ET.SubElement(xml.getroot(), "streets")

    # Some edges might already have a street, so we want to ignore those
    known_streets = {street.attrib["edge"]: street for street in streets.findall("street")}

    for edge in net.getEdges():
        eid = edge.getID()
        if eid not in known_streets:
            # This edge is missing a street entry. Find population and industry for this edge
            population = get_population_number(edge=edge, base=POPULATION_BASE, scale=scale, octaves=octaves,
                                               centre=centre, radius=radius)
            industry = get_population_number(edge=edge, base=INDUSTRY_BASE, scale=scale, octaves=octaves,
                                             centre=centre, radius=radius)

            ET.SubElement(streets, "street", {
                "edge": eid,
                "population": str(population),
                "workPosition": str(industry)
            })


def radius_of_network(net: sumolib.net.Net, centre):
    """
    Get distance from centre to outermost node. Use this for computing radius of network.
    FIXME: if centre is given off-center, it will return the largest distance from the centre which is not the radius
    :return: the radius of the network
    """
    return np.max([distance(centre, node.getCoord()) for node in net.getNodes()])


def distance(pos1, pos2):
    """
    Get hypotenuse using Phytagoras theorem
    :return: the distance between pos1 and pos2
    """
    x1, y1 = pos1
    x2, y2 = pos2
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def display_noisemap(net: sumolib.net.Net, scale: float, octave: int):
    """
    Draw an image of the noisemap applied to a given network. Currently only displaying residential densities.
    FIXME: do residential and industrial in different colours
    :param net:
    :return:
    """
    boundary = net.getBoundary()
    size = (boundary[2], boundary[3])
    from randomActivityGen import find_city_centre
    centre = find_city_centre(net)
    radius = radius_of_network(net, centre)

    arr = [[0 for x in range(int(size[0]))] for x in range(int(size[1]))]
    for i in range(0, int(size[0])):
        for j in range(0, int(size[1])):
            p_noise = get_perlin_noise(i, j, base=POPULATION_BASE, scale=scale, octaves=octave)
            arr[i][j] = p_noise + (1 - (distance((i, j), centre) / radius))

    toimage(arr).show()
