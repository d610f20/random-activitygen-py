import os
import sys
import xml.etree.ElementTree as ET
from xml.etree import ElementTree
import random

import noise
import numpy as np

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib

# The 'noise' lib has good resolution until above 10 mil, but a SIGSEGV is had on values above [-100000, 100000]
POPULATION_BASE = random.randrange(-100000, 100000)
INDUSTRY_BASE = random.randrange(-100000, 100000)


def get_edge_pair_centroid(coords: list) -> (float, float):
    """
    Centroid of rectangle (edge_pair) = (width/2, height/2)
    :param coords: [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)]
    :return: Centroid of given shape
    """
    x_avg = np.mean([pos[0] for pos in coords])
    y_avg = np.mean([pos[1] for pos in coords])
    return x_avg, y_avg


def normalise_noise(noise_val: float) -> float:
    """
    The 'noise' lib returns a value in the range of [-1:1]. The noise value is scaled to the range of [0:1].
    :param noise_val: a float [-1:1]
    :return: the noise value scaled to [0:1]
    """
    return (noise_val + 1) / 2


def get_perlin_noise(x: float, y: float, base: float) -> float:
    """
    :param base: offset into noisemap
    :param x: the sample point for x
    :param y: the sample point for y
    :return: a normalised float of the sample in noisemap
    """
    return normalise_noise(noise.pnoise2(x, y, base=base))


def get_population_number(net: sumolib.net.Net, edge, base: float) -> float:
    """
    Returns a Perlin simplex noise at centre of given street
    :param base: offset into noisemap
    :param net: the SUMO network
    :param edge: the edge ID
    :return: the scaled noise value as float in [0:1]
    """
    x, y = get_edge_pair_centroid(net.getEdge(edge).getShape())
    return get_perlin_noise(x, y, base)


def apply_network_noise(net: sumolib.net.Net, xml: ElementTree):
    """
    Calculate and apply Perlin noise in [0:1] range for each street for population and industry
    :param net: the SUMO network
    :param xml: the statistics XML for the network
    :return:
    """
    for edge in list(map(lambda x: x.getID(), net.getEdges())):
        population = get_population_number(net, edge, POPULATION_BASE)
        industry = get_population_number(net, edge, INDUSTRY_BASE)

        for street in xml.find("streets").findall("street"):
            if street.attrib["edge"] == edge:
                street.set("population", str(population))
                street.set("workPosition", str(industry))


def apply_perlin_noise(net: sumolib.net.Net, stats: ET.ElementTree):
    # Calculate and apply Perlin noise for all edges in network to population in statistics
    print("Writing Perlin noise to population and industry")
    apply_network_noise(net, stats)
