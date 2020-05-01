import logging
import os
import sys
import xml.etree.ElementTree as ET
from typing import List, Tuple
from xml.etree import ElementTree

import noise
import numpy as np

from utility import distance, radius_of_network, smoothstep

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib

POPULATION_BASE = -1  # Initialized in main
INDUSTRY_BASE = -1  # Initialized in main


def get_edge_pair_centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Centroid of rectangle (edge_pair) = (width/2, height/2)
    :param coords: [(x_1,y_1), (x_2,y_2), ... , (x_n,y_n)]
    :return: Centroid of given shape
    """
    x_avg = np.mean([pos[0] for pos in coords])
    y_avg = np.mean([pos[1] for pos in coords])
    return float(x_avg), float(y_avg)


def get_perlin_noise(x: float, y: float, base: int, scale: float = 0.005, octaves: int = 3) -> float:
    """
    The 'noise' lib returns a value in the range of [-1:1]. The noise value is scaled to the range of [0:1].
    :param x: the sample point for x
    :param y: the sample point for y
    :param base: the offset for the 2d slice
    :param scale: the scale to multiply to each coordinate, default is 0.005
    :param octaves: the octaves to use when sampling, default is 3
    :return: a normalised float of the sample in noisemap
    """
    return (noise.pnoise3(x=x * scale, y=y * scale, z=base, octaves=octaves) + 1) / 2


def sample_edge_noise(edge: sumolib.net.edge.Edge, base: int, centre,
                      radius, centre_weight: float = 1.0, scale: float = 0.005, octaves: int = 3) -> float:
    """
    Returns a normalised Perlin noise sample at centre of given edge
    :param edge: the edge
    :param base: offset into noisemap
    :param centre: centre of the city
    :param radius: radius of the city
    :param centre_weight: how much impact being near the centre has
    :param scale: the scale to multiply to each coordinate, default is 0.005
    :param octaves: the octaves to use when sampling, default is 3
    :return: the value between [0:1]
    """
    x, y = get_edge_pair_centroid(edge.getShape())
    noise_value = get_perlin_noise(x, y, base=base, scale=scale, octaves=octaves)
    gradient = (1 - (distance((x, y), centre) / radius))
    # Normalise value to [0..1] range by dividing with its max potential value
    return (smoothstep(noise_value) + gradient * centre_weight) / (1 + centre_weight)


def apply_network_noise(net: sumolib.net.Net, xml: ElementTree, centre: Tuple[float, float], centre_pop_weight: float,
                        centre_work_weight: float):
    """
    Calculate and apply Perlin noise in [0:1] range for each street for population and industry
    :param net: the SUMO network
    :param xml: the statistics XML for the network
    :param centre: the city's centre/downtown
    :param centre_pop_weight: how much impact being near the centre has for population
    :param centre_work_weight: how much impact being near the centre has for industry
    :return:
    """
    # Calculate and apply Perlin noise for all edges in network to population in statistics
    logging.debug(f"City centre: {centre}")
    radius = radius_of_network(net, centre)
    logging.debug(f"City radius: {radius:.2f}")
    noise_scale = 4 / radius
    logging.debug(f"Using noise scale: {noise_scale:.2f}")

    streets = xml.find("streets")
    if streets is None:
        streets = ET.SubElement(xml.getroot(), "streets")

    # Some edges might already have a street, so we want to ignore those
    known_streets = {street.attrib["edge"]: street for street in streets.findall("street")}

    for edge in net.getEdges():
        eid = edge.getID()
        if eid not in known_streets:
            # This edge is missing a street entry. Find population and industry for this edge
            population = sample_edge_noise(edge=edge, base=POPULATION_BASE, scale=noise_scale, octaves=3,
                                           centre=centre, radius=radius, centre_weight=centre_pop_weight)
            industry = sample_edge_noise(edge=edge, base=INDUSTRY_BASE, scale=noise_scale, octaves=3,
                                         centre=centre, radius=radius, centre_weight=centre_work_weight)

            logging.debug(f"Adding street with eid: {eid},\t population: {population:.4f}, industry: {industry:.4f}")
            ET.SubElement(streets, "street", {
                "edge": eid,
                "population": str(population),
                "workPosition": str(industry)
            })
