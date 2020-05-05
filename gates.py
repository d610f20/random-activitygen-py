import logging
import os
import random
import math
import sys

import numpy as np
import xml.etree.ElementTree as ET

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def setup_city_gates(net: sumolib.net.Net, stats: ET.ElementTree, gate_count: int):
    assert gate_count >= 0, "Number of city gates cannot be negative"
    # Find existing gates to determine how many we need to insert
    xml_gates = stats.find("cityGates")
    if xml_gates is None:
        xml_gates = ET.SubElement(stats.getroot(), "cityGates")
    xml_entrances = xml_gates.findall("entrance")
    n = gate_count - len(xml_entrances)
    if n < 0:
        logging.debug(
            f"[gates] {gate_count} city gate were requested, but there are already {len(xml_entrances)} defined")
    if n <= 0:
        return
    logging.debug(f"[gates] Inserting {n} new city gates")

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
    base_rad = random.random() * math.tau
    rads = [(base_rad + i * math.tau / n) % math.tau for i in range(0, n)]
    directions = [(math.cos(rad), math.sin(rad)) for rad in rads]

    for direction in directions:
        # Find the dead ends furthest in each direction using the dot product and argmax. Those nodes will be our gates.
        # Dead ends are removed from the list to avoid duplicates.
        gate_index = int(np.argmax([np.dot(node.getCoord(), direction) for node in dead_ends]))
        gate = dead_ends[gate_index]
        dead_ends.remove(gate)

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
        edge, pos = (gate.getOutgoing()[0], 0) if len(gate.getOutgoing()) > 0 \
            else (gate.getIncoming()[0], gate.getIncoming()[0].getLength())
        logging.debug(
            f"Adding entrance to statistics, edge: {edge.getID()}, incoming traffic: {incoming_traffic}, outgoing "
            f"traffic: {outgoing_traffic}")
        ET.SubElement(xml_gates, "entrance", attrib={
            "edge": edge.getID(),
            "incoming": str(incoming_traffic),
            "outgoing": str(outgoing_traffic),
            "pos": str(pos)
        })
