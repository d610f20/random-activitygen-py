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


def setup_city_gates(net: sumolib.net.Net, stats: ET.ElementTree, gate_count: str, city_radius: float):
    """
    Generate the requested amount of city gates based on the network and insert them into stats.
    """

    gate_count = find_gate_count_auto(city_radius) if gate_count == "auto" else int(gate_count)
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

    # Find all nodes that are dead ends, i.e. nodes that only have one neighbouring node
    # and at least one of the connecting edges is a road (as opposed to path) and allows private vehicles
    dead_ends = [node for node in net.getNodes() if len(node.getNeighboringNodes()) == 1
                 and any([any([lane.allows("private") for lane in edge.getLanes()]) for edge in
                          node.getIncoming() + node.getOutgoing()])]

    # Pick random dead ends as gates
    random.shuffle(dead_ends)

    for gate in dead_ends[:n]:

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
            f"[gates] Adding entrance to statistics, edge: {edge.getID()}, incoming traffic: {incoming_traffic}, outgoing "
            f"traffic: {outgoing_traffic}")
        ET.SubElement(xml_gates, "entrance", attrib={
            "edge": edge.getID(),
            "incoming": str(incoming_traffic),
            "outgoing": str(outgoing_traffic),
            "pos": str(pos)
        })


def find_gate_count_auto(city_radius: float) -> int:
    # Assume there's a gate very 1750 meters around the circumference
    circumference = 2 * city_radius * math.pi
    return int(circumference / 1750)
