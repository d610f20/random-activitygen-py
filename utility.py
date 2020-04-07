import logging
import os
import sys
import random
import math

import numpy as np
from typing import Tuple
import xml.etree.ElementTree as ET

from docopt import Dict

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
        logging.info("Population is missing from statistics, adding a default configuration")
        population = ET.SubElement(city, "population")
        ET.SubElement(population, "bracket", {"beginAge": "0", "endAge": "30", "peopleNbr": "30"})
        ET.SubElement(population, "bracket", {"beginAge": "30", "endAge": "60", "peopleNbr": "40"})
        ET.SubElement(population, "bracket", {"beginAge": "60", "endAge": "90", "peopleNbr": "30"})

    # Similarly at least and one opening and closing workhour is required
    work_hours = city.find("workHours")
    if work_hours is None:
        # Work hours are missing, so we add some default work hours
        logging.info("Work hours are missing from statistics, adding a default configuration")
        work_hours = ET.SubElement(city, "workHours")
        ET.SubElement(work_hours, "opening", {"hour": "28800", "proportion": "70"})  # 70% at 8.00
        ET.SubElement(work_hours, "opening", {"hour": "30600", "proportion": "30"})  # 30% at 8.30
        ET.SubElement(work_hours, "closing", {"hour": "43200", "proportion": "10"})  # 10% at 12.00
        ET.SubElement(work_hours, "closing", {"hour": "61200", "proportion": "30"})  # 30% at 17.00
        ET.SubElement(work_hours, "closing", {"hour": "63000", "proportion": "60"})  # 60% at 17.30


def setup_city_gates(net: sumolib.net.Net, stats: ET.ElementTree, gate_count: int):
    assert gate_count >= 0, "Number of city gates cannot be negative"
    # Find existing gates to determine how many we need to insert
    xml_gates = stats.find("cityGates")
    if xml_gates is None:
        xml_gates = ET.SubElement(stats.getroot(), "cityGates")
    xml_entrances = xml_gates.findall("entrance")
    n = gate_count - len(xml_entrances)
    if n < 0:
        logging.warning(f"{gate_count} city gate were requested, but there are already {len(xml_entrances)} defined")
    if n <= 0:
        return
    logging.info(f"Inserting {n} new city gates")

    # Finds all nodes that are dead ends, i.e. nodes that only have one neighbouring node
    # and at least one of the connecting edges is a road (as opposed to path) and allows private vehicles
    dead_ends = [node for node in net.getNodes() if len(node.getNeighboringNodes()) == 1
                 and any([any([lane.allows("private") for lane in edge.getLanes()]) for edge in
                          node.getIncoming() + node.getOutgoing()])]

    # Find n unit vectors pointing in different directions
    # If n = 4 and base_rad = 0 we get the cardinal directions:
    #      N
    #      |
    # W<---o--->E
    #      |
    #      S
    tau = math.pi * 2
    base_rad = random.random() * tau
    rads = [(base_rad + i * tau / n) % tau for i in range(0, n)]
    dirs = [(math.cos(rad), math.sin(rad)) for rad in rads]

    for dir in dirs:
        # Find the dead ends furthest in each direction using the dot product and argmax. Those nodes will be our gates.
        # Duplicates are possible and no problem. That just means there will be more traffic through that gate.
        gate_index = int(np.argmax([np.dot(node.getCoord(), dir) for node in dead_ends]))
        gate = dead_ends[gate_index]

        # Decide proportion of the incoming and outgoing vehicles coming through this gate
        # These numbers are relatively to the values of the other gates
        # The number is proportional to the number of lanes allowing private vehicles
        incoming_lanes = sum(
            [len([lane for lane in edge.getLanes() if lane.allows("private")]) for edge in gate.getIncoming()])
        outgoing_lanes = sum(
            [len([lane for lane in edge.getLanes() if lane.allows("private")]) for edge in gate.getOutgoing()])
        incoming_traffic = (1 + random.random()) * outgoing_lanes
        outgoing_traffic = (1 + random.random()) * incoming_lanes

        # Add entrance to stats file
        edge = gate.getOutgoing()[0] if len(gate.getOutgoing()) > 0 else gate.getIncoming()[0]
        logging.debug(
            f"Adding entrance to statistics, edge: {edge.getID()}, incoming traffic: {incoming_traffic}, outgoing "
            f"traffic: {outgoing_traffic}")
        ET.SubElement(xml_gates, "entrance", attrib={
            "edge": edge.getID(),
            "incoming": str(incoming_traffic),
            "outgoing": str(outgoing_traffic),
            "pos": "0"
        })


def position_on_edge(edge: sumolib.net.edge.Edge, pos: int):
    """
    :return: coordinate for pos meters from the start of the edge, following any shapes along edge
    """
    # Go through pair of coords, until meeting an edge, where if we travel through it, we have moved more than pos
    # meters in total
    remaining_distance = pos
    for coord1, coord2 in (edge.getShape()[i:i + 2] for i in range(0, int(len(edge.getShape())), 2)):
        if 0 < remaining_distance - distance(coord1, coord2):
            remaining_distance -= distance(coord1, coord2)
        else:
            break

    # Subtract the vector coord1 from vector coord2
    vec = np.subtract([coord2[0], coord2[1]], [coord1[0], coord1[1]])

    # Normalize it by dividing by its own length
    unit_vec = vec / np.linalg.norm(vec)

    # Scale by remaining distance
    unit_vec_scaled = unit_vec * remaining_distance

    # Add this scaled vector to the start point, to find the correct coord that is at remaining distance from this
    # coord, to coord2
    return coord1[0] + unit_vec_scaled[0], coord1[1] + unit_vec_scaled[1]


def setup_logging(args: Dict):
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
