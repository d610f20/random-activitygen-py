import os
import sys
import xml.etree.ElementTree as ET
from xml.etree import ElementTree

import noise
import numpy as np

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def get_edge_pair_centroid(coords: list) -> (float, float):
    """
    Centroid of rectangle (edge_pair) = (width/2, height/2)
    :param coords: [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)]
    :return: Centroid of given shape
    """
    x_avg = np.mean([pos[0] for pos in coords])
    y_avg = np.mean([pos[1] for pos in coords])
    return x_avg, y_avg


def normalise_noise(noise: float) -> float:
    """
    The 'noise' lib returns a value in the range of [-1:1]. The noise value is scaled to the range of [0:1].
    :param noise: a float [-1:1]
    :return: the noise value scaled to [0:1]
    """
    return (noise + 1) / 2


def get_perlin_noise(x, y) -> float:
    """
    TODO: Find sane offset to combat zero-value at (0, 0)
    :param x:
    :param y:
    :return:
    """
    return normalise_noise(noise.pnoise2(x, y))


def get_population_number(net: sumolib.net.Net, edge) -> float:
    """
    Returns a Perlin simplex noise at centre of given street
    :param net: the SUMO network
    :param edge: the edge ID
    :return: the scaled noise value as float in [0:1]
    """
    x, y = get_edge_pair_centroid(net.getEdge(edge).getShape())
    return get_perlin_noise(x, y)


def calculate_network_population(net: sumolib.net.Net, xml: ElementTree):
    """
    Calculate and apply the Perlin noise in [0:1] range for each street
    :param net: the SUMO network
    :param xml: the statistics XML for the network
    :return:
    """
    for edge in list(map(lambda x: x.getID(), net.getEdges())):
        pop = get_population_number(net, edge)
        streets = xml.find("streets").findall("street")
        for street in streets:
            if street.attrib["edge"] == edge:
                street.set("population", str(pop))


def apply_perlin_noise(net_path: str, statistics_path: str):
    # Read in SUMO network
    net = sumolib.net.readNet(net_path)

    # Parse statistics configuration
    stats = ET.parse(statistics_path)

    # Calculate and apply Perlin noise for all edges in network to population in statistics
    calculate_network_population(net, stats)

    # Write statistics back
    stats.write(statistics_path)


if __name__ == '__main__':
    apply_perlin_noise("in/example.net.xml", "in/example.stat.xml")
