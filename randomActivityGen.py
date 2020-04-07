"""Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--gates.count=N] [--display]
    ([--quiet] | [--verbose] | [--log-level=LEVEL]) [--log-file=FILENAME]

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    --gates.count N             Number of city gates in the city [default: 4]
    --display                   Displays an image of cities elements and the noise used to generate them.
    --verbose                   Sets log-level to DEBUG
    --quiet                     Sets log-level to ERROR
    --log-level=<LEVEL>         Explicitly set log-level {DEBUG, INFO, WARN, ERROR, CRITICAL} [default: INFO]
    --log-file=<FILENAME>       Set log filename [default: randomActivityGen-log.txt]
    -h, --help                  Show this screen.
    --version                   Show version.
"""
import math
import os
import random
import sys
import xml.etree.ElementTree as ET
import logging
import numpy as np
from docopt import docopt

from perlin import apply_network_noise
from render import display_network

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


def verify_stats(stats: ET.ElementTree):
    """
    Do various verification on the stats file to ensure that it is usable. If population and work hours are missing,
    some default values will be insert as these are required by ActivityGen.

    :param stats: stats file parsed with ElementTree
    """
    city = stats.getroot()
    assert city.tag == "city", "Stat file does not seem to be a valid stat file. The root element is not city"
    # According to ActivityGen (https://github.com/eclipse/sumo/blob/master/src/activitygen/AGActivityGenHandler.cpp#L124-L161)
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


def main():
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    # Setup logging
    logger = logging.getLogger()
    log_stream_handler = logging.StreamHandler(sys.stdout)
    # Setup file logger, use given or default filename, and overwrite logs on each run
    log_file_handler = logging.FileHandler(filename=args["--log-file"], mode="w")
    # Write log-level and indent slightly for message
    stream_formatter = logging.Formatter('%(levelname)-8s %(message)s')
    # Use more verbose format for logfile
    log_file_handler.setFormatter(logging.Formatter("%(asctime)s,%(msecs)d %(levelname)-8s %(message)s"))
    log_stream_handler.setFormatter(stream_formatter)
    logger.addHandler(log_stream_handler)
    # FIXME: logfile should always print in DEBUG
    logger.addHandler(log_file_handler)

    # Parse log-level
    if args["--quiet"]:
        log_level = logging.ERROR
    elif args["--verbose"]:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, str(args["--log-level"]).upper())

    logger.setLevel(log_level)

    # Read in SUMO network
    logging.info(f"Reading network from: {args['--net-file']}")
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    logging.info(f"Parsing stat file: {args['--stat-file']}")
    stats = ET.parse(args["--stat-file"])
    verify_stats(stats)

    # Scale and octave seems like sane values for the moment
    logging.info("Writing Perlin noise to population and industry")
    noise_scale = 0.005
    noise_octaves = 3
    logging.debug(f"Perlin noise using scale: {noise_scale}, octaves: {noise_octaves}")
    apply_network_noise(net, stats, noise_scale, noise_octaves)

    logging.info(f"Setting up {int(args['--gates.count'])} city gates ")
    setup_city_gates(net, stats, int(args["--gates.count"]))

    # Write statistics back
    logging.info(f"Writing statistics file to {args['--output-file']}")
    stats.write(args["--output-file"])

    if args["--display"]:
        x_size, y_size = 500, 500
        logging.info(f"Displaying network as image sized: {x_size} x {y_size}")
        display_network(net, stats, x_size, y_size)


if __name__ == "__main__":
    main()
