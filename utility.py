import os
import sys
import numpy as np
from typing import Tuple

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


def position_on_edge(edge: sumolib.net.edge.Edge, pos: int):
    """
    :return: coordinate for pos meters from the start of the edge, following any shapes along edge
    """
    # Go through pair of coords, until meeting an edge, where if we travel through it, we have moved more than pos
    # meters in total
    remaining_distance = pos
    for coord1, coord2 in (edge.getShape()[i:i + 2] for i in range(0, int(len(edge.getShape()) / 2 * 2), 2)):
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
