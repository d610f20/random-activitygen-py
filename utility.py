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


def linear_equation(pos1: Tuple[float, float], pos2: Tuple[float, float]):
    x_coords = [pos1[0], pos2[0]]
    y_coords = [pos1[1], pos2[1]]
    a, b = np.polyfit(x_coords, y_coords, 1)

    def f(x):
        return b + a * x

    return f


def position_on_edge(edge: sumolib.net.edge.Edge, pos: int):
    """
    :return: coordinate for pos meters from the start of the edge, following any shapes along edge
    """
    # Go through pair of coords, until meeting an edge, where if we travel through it, we have moved more than pos meters
    remaining_distance = pos
    for coord1, coord2 in (edge.getShape()[i:i + 2] for i in range(0, int(len(edge.getShape()) / 2 * 2), 2)):
        if 0 < remaining_distance - distance(coord1, coord2):
            remaining_distance -= distance(coord1, coord2)
        else:
            first_cord = coord1
            second_cord = coord2
            break

    # Now we have the final edge where we need to find a location on.
    # Find a linear equation from start to end of this stretch
    f = linear_equation(first_cord, second_cord)

    # TODO use lerp and vectors instead of computing equation
    # Potential coordinate for the correct position. Start at coord1.
    pos_coords = (first_cord[0], first_cord[1])

    # Move x one each iteration and calculate distance from this next position, and coord1.
    # When we find a position that is larger than remaining distance, return the coordinate just before this.
    while distance(first_cord, pos_coords) < remaining_distance:
        # Go right
        if (first_cord[0] < second_cord[0]):
            pos_coords = (pos_coords[0] + 1, f(pos_coords[0] + 1))

        # Go left
        if (first_cord[0] > second_cord[0]):
            pos_coords = (pos_coords[0] - 1, f(pos_coords[0] - 1))

    # return position coords
    return pos_coords[0], pos_coords[1]
