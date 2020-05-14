import logging
import os
import sys
import xml.etree.ElementTree as ET
from typing import Tuple

import numpy as np
from scipy.cluster.vq import kmeans

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_city_centre(net: sumolib.net.Net) -> Tuple[float, float]:
    """
    Finds the city centre; average node coord of all nodes in the net
    """
    node_coords = [node.getCoord() for node in net.getNodes()]
    return float(np.mean([c[0] for c in node_coords])), float(np.mean([c[1] for c in node_coords]))


def radius_of_network(net: sumolib.net.Net, centre: Tuple[float, float]):
    """
    Get distance from centre to outermost node. Use this for computing radius of network.
    :return: the radius of the network
    """
    return np.max([distance(centre, node.getCoord()) for node in net.getNodes()])


def distance(pos1: Tuple[float, float], pos2: Tuple[float, float]):
    """
    Return the distance between two points in a plane
    :return: the distance between pos1 and pos2
    """
    x1, y1 = pos1
    x2, y2 = pos2
    return np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def k_means_clusters(net: sumolib.net.Net, k: int):
    """
    Return k clusters of edges from running k-means on net file
    :param net: the net whose edges should be partitioned to clusters
    :param k: how many clusters the network should be divided into
    """
    from perlin import get_edge_pair_centroid
    edges = net.getEdges()

    centroid_edges = [get_edge_pair_centroid(edge.getShape()) for edge in edges]
    centroids = kmeans(np.array(centroid_edges), k, iter=25)

    clusters = [[] for _ in range(k)]
    # Iterate through each edge, to decide which cluster it belongs to
    for edge in edges:
        # Find the center point of the edge, and set distance to first centroid returned from kmeans
        edge_centroid = get_edge_pair_centroid(edge.getShape())
        minimum = distance(edge_centroid, centroids[0][0])

        correct_index = 0

        # Iterate though each centroid from k-means, and find the centroid to which the current edge has lowest
        # distance to
        for i, centroid in enumerate(centroids[0]):
            if distance(edge_centroid, centroid) < minimum:
                minimum = distance(edge_centroid, centroid)
                correct_index = i

        clusters[correct_index].append(edge)

    return clusters


def verify_stats(stats: ET.ElementTree):
    """
    Do various verification on the stats file to ensure that it is usable. If population and work hours are missing,
    some default values will be insert as these are required by ActivityGen.

    :param stats: stats file parsed with ElementTree
    """
    city = stats.getroot()
    assert city.tag == "city", "Stat file does not seem to be a valid stat file. The root element is not city"
    # According to ActivityGen
    # (https://github.com/eclipse/sumo/blob/master/src/activitygen/AGActivityGenHandler.cpp#L124-L161)
    # only general::inhabitants and general::households are required. Everything else has default values.
    general = stats.find("general")
    # TODO Maybe guestimate the number of inhabitants and households based on the network's size
    assert general is not None, "Stat file is missing <general>. Inhabitants and households are required"
    assert general.attrib["inhabitants"] is not None, "Number of inhabitants are required"
    assert general.attrib["households"] is not None, "Number of households are required"

    # It is also required that there are at least one population bracket
    population = city.find("population")
    if population is None:
        # Population is missing, so we add a default population
        logging.info("[utility] Population is missing from statistics, adding a default configuration")
        population = ET.SubElement(city, "population")
        ET.SubElement(population, "bracket", {"beginAge": "0", "endAge": "30", "peopleNbr": "30"})
        ET.SubElement(population, "bracket", {"beginAge": "30", "endAge": "60", "peopleNbr": "40"})
        ET.SubElement(population, "bracket", {"beginAge": "60", "endAge": "90", "peopleNbr": "30"})

    # Similarly at least and one opening and closing workhour is required
    work_hours = city.find("workHours")
    if work_hours is None:
        # Work hours are missing, so we add some default work hours based on Danish work hours
        logging.info("[utility] Work hours are missing from statistics, adding a default configuration")
        work_hours = ET.SubElement(city, "workHours")
        ET.SubElement(work_hours, "opening", {"hour": "25200", "proportion": "15"})  # 15% at 7.00
        ET.SubElement(work_hours, "opening", {"hour": "27000", "proportion": "25"})  # 25% at 7.30
        ET.SubElement(work_hours, "opening", {"hour": "28800", "proportion": "45"})  # 45% at 8.00
        ET.SubElement(work_hours, "opening", {"hour": "30600", "proportion": "15"})  # 15% at 8.30
        ET.SubElement(work_hours, "closing", {"hour": "43200", "proportion": "5"})  # 5% at 12.00
        ET.SubElement(work_hours, "closing", {"hour": "54000", "proportion": "20"})  # 20% at 15.00
        ET.SubElement(work_hours, "closing", {"hour": "55800", "proportion": "30"})  # 30% at 15.30
        ET.SubElement(work_hours, "closing", {"hour": "57600", "proportion": "30"})  # 30% at 16.00
        ET.SubElement(work_hours, "closing", {"hour": "59400", "proportion": "15"})  # 15% at 16.30


def position_on_edge(edge: sumolib.net.edge.Edge, pos: float):
    """
    :return: coordinate achieved by moving along the edge by pos meters.
    """
    # Go through pair of coords, until meeting an edge, where if we travel through it, we have moved more than pos
    # meters in total
    coord1, coord2 = None, None
    remaining_distance = pos
    for coord1, coord2 in [edge.getShape()[i:i + 2] for i in range(0, int(len(edge.getShape())-1))]:
        if 0 < remaining_distance - distance(coord1, coord2):
            remaining_distance -= distance(coord1, coord2)
        else:
            break

    assert coord1 is not None and coord2 is not None, "Coordinates was none, cannot get position on edge"

    # Subtract the vector coord1 from vector coord2
    vec = np.subtract([coord2[0], coord2[1]], [coord1[0], coord1[1]])

    # Normalize it by dividing by its own length
    unit_vec = vec / np.linalg.norm(vec)

    # Scale by remaining distance
    unit_vec_scaled = unit_vec * remaining_distance

    # Add this scaled vector to the start point, to find the correct coord that is at remaining distance from this
    # coord, to coord2
    return coord1[0] + unit_vec_scaled[0], coord1[1] + unit_vec_scaled[1]


def setup_logging(args: dict):
    """
    Create a stdout- and file-handler for logging framework.
    FIXME: logfile should always print in DEBUG, this seems like a larger hurdle, see:
    https://stackoverflow.com/questions/25187083/python-logging-to-multiple-handlers-at-different-log-levels
    :return:
    """
    logger = logging.getLogger()
    log_stream_handler = logging.StreamHandler(sys.stdout)
    # Write log-level and indent slightly for message
    stream_formatter = logging.Formatter('%(levelname)-8s %(message)s')

    # Setup file logger, use given or default filename, and overwrite logs on each run
    log_file_handler = logging.FileHandler(filename=args["--log-file"], mode="w")
    # Use more verbose format for logfile
    log_file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
    log_stream_handler.setFormatter(stream_formatter)

    # Parse log-level
    if args["--quiet"]:
        log_level = logging.ERROR
    elif args["--verbose"]:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, str(args["--log-level"]).upper())

    # Set log-levels and add handlers
    log_file_handler.setLevel(log_level)
    logger.addHandler(log_stream_handler)
    logger.setLevel(log_level)

    # FIXME: Following line does not take effect
    log_file_handler.setLevel(logging.DEBUG)
    logger.addHandler(log_file_handler)


def smoothstep(t: float):
    """
    A sigmoid-like tweening function
    """
    return t * t * (3 - 2 * t)


def firstn(n, gen):
    """
    Restricts generator to yields at most N element
    """
    for _ in range(0, n):
        yield next(gen)
