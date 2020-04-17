import math
import random
import xml.etree.ElementTree as ET
import os
import sys
import logging

from typing import Tuple
from perlin import POPULATION_BASE, sample_edge_noise
from utility import find_city_centre, radius_of_network, k_means_clusters

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_bus_stop_edges(net: sumolib.net.Net, num_bus_stops: int, centre: Tuple[float, float]):
    # Use k-means, to split the net into num_num_bus_stops number of clusters,
    # each containing approximately same number of edges
    districts = k_means_clusters(net, num_bus_stops)

    bus_stop_edges = []
    centre = find_city_centre(net)
    radius = radius_of_network(net, centre)
    # Sort each edge in each district based on their noise, and select edge with highest noise from each district
    for district in districts:
        district.sort(key=lambda x: sample_edge_noise(x, centre=centre, radius=radius, base=POPULATION_BASE))
        bus_stop_edges.append(district[-1])

    return bus_stop_edges


def setup_bus_stops(net: sumolib.net.Net, stats: ET.ElementTree, bus_stops_per_km2: float,
                    centre: Tuple[float, float]):

    xml_bus_stops = stats.find('busStations')
    if xml_bus_stops is None:
        xml_bus_stops = ET.SubElement(stats.getroot(), "busStations")

    boundary = net.getBoundary()
    width = boundary[2] - boundary[0]
    height = boundary[3] - boundary[1]

    area = math.pi * ((width + height) / 4) ** 2
    num_bus_stops = int(bus_stops_per_km2 * area / 1_000_000)
    logging.info(f"Inserting {num_bus_stops} bus stops")

    # Find edges to place bus stops on
    bus_stop_edges = find_bus_stop_edges(net, num_bus_stops, centre)
    for i, edge in enumerate(bus_stop_edges):
        ET.SubElement(xml_bus_stops, "busStation", attrib={
            "id": str(i),
            "edge": str(edge.getID()),
            "pos": str(random.random() * edge.getLength()),
        })
