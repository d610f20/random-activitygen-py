"""Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--centre.pos=args]
    [--centre.pop-weight=F] [--centre.work-weight=F] [--gates.count=N] [--schools.stepsize=F] [--schools.open=args]
    [--schools.close=args]  [--primary-school.begin-age=args] [--primary-school.end-age=args] [--primary-school.count=N]
    [--primary-school.ratio=F] [--primary-school.capacity=args] [--high-school.begin-age=args]
    [--high-school.end-age=args] [--high-school.count=N] [--high-school.ratio=F] [--high-school.capacity=args]
    [--college.begin-age=args] [--college.end-age=args] [--college.count=N] [--college.ratio=F]
    [--college.capacity=args] [--bus-stop.distance=N] [--bus-stop.k=N] [--display] [--display.size=N]
    [--seed=S | --random] ([--quiet] | [--verbose] | [--log-level=LEVEL]) [--log-file=FILENAME]

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    --centre.pos args           The coordinates for the city's centre, e.g. "300,500" or "auto" [default: auto]
    --centre.pop-weight F       The increase in population near the city center [default: 0.8]
    --centre.work-weight F      The increase in work places near the city center [default: 0.1]
    --gates.count N             Number of city gates in the city [default: 4]
    --schools.stepsize F        Stepsize in opening/closing hours, in parts of an hour, e.g 0.25 is every 15 mins [default: 0.25]
    --schools.open=args         The interval at which the schools opens (24h clock) [default: 7,10]
    --schools.close=args        The interval at which the schools closes (24h clock) [default: 13,17]
    --primary-school.count N           Number of schools in the city, if not used, number of schools is based on population [default: auto]
    --primary-school.ratio F           Number of schools per 1000 inhabitants [default: 0.2]
    --primary-school.begin-age=args    The range of ages at which students start going to school [default: 6,14]
    --primary-school.end-age=args      The range of ages at which students stops going to school [default: 12,16]
    --primary-school.capacity=args     The range for capacity in schools [default: 100,500]
    --high-school.count N           Number of schools in the city, if not used, number of schools is based on population [default: auto]
    --high-school.ratio F           Number of schools per 1000 inhabitants [default: 0.04]
    --high-school.begin-age=args    The range of ages at which students start going to school [default: 15,18]
    --high-school.end-age=args      The range of ages at which students stops going to school [default: 18,23]
    --high-school.capacity=args     The range for capacity in schools [default: 500,1000]
    --college.count N           Number of schools in the city, if not used, number of schools is based on population [default: auto]
    --college.ratio F           Number of schools per 1000 inhabitants [default: 0.015]
    --college.begin-age=args    The range of ages at which students start going to school [default: 19,25]
    --college.end-age=args      The range of ages at which students stops going to school [default: 24,29]
    --college.capacity=args     The range for capacity in schools [default: 1000,2000]
    --bus-stop.distance N       Minimum distance between bus stops [default: 500]
    --bus-stop.k N              Placement attempts in the poisson-disc algorithm [default: 10]
    --display                   Displays an image of cities elements and the noise used to generate them.
    --display.size N            Set max width and height of image to display to N [default: 800]
    --verbose                   Sets log-level to DEBUG
    --quiet                     Sets log-level to ERROR
    --log-level=<LEVEL>         Explicitly set log-level {DEBUG, INFO, WARN, ERROR, CRITICAL} [default: INFO]
    --log-file=<FILENAME>       Set log filename [default: randomActivityGen-log.txt]
    --seed S                    Initialises the random number generator with the given value S [default: 31415]
    --random                    Initialises the random number generator with the current system time [default: false]
    -h, --help                  Show this screen.
    --version                   Show version.
"""

import os
import random
import sys
import xml.etree.ElementTree as ET

import logging

from docopt import docopt
from school import setup_schools
from perlin import apply_network_noise
from utility import find_city_centre, verify_stats, setup_logging, position_on_edge
from gates import setup_city_gates
from render import display_network
from bus import bus_stop_generator

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def setup_bus_stops(net: sumolib.net.Net, stats: ET.ElementTree, min_distance, k):
    logging.debug(f"[bus-stops] Using min_distance: {min_distance}, and k (attempts): {k}")
    edges = net.getEdges()

    city = stats.getroot()
    bus_stations = city.find("busStations")
    seed_bus_stops = []
    if bus_stations is None:
        bus_stations = ET.SubElement(city, "busStations")
    else:
        for station in bus_stations.findall("busStation"):
            assert "edge" in station.attrib, "BusStation isn't placed on an edge"
            edge_id = station.attrib["edge"]
            assert "pos" in station.attrib, "BusStation doesn't have a position along the edge"
            along = float(station.attrib["pos"])

            edge = net.getEdge(edge_id)
            if edge is None:
                logging.warning("BusStation in stat file reference edge (id=\"{}\") that doesn't exist in the road "
                                "network".format(edge_id))
                continue

            pos = position_on_edge(edge, along)

            seed_bus_stops.append([
                pos[0],
                pos[1],
                edge,
                along])

    for i, busstop in enumerate(bus_stop_generator(edges, min_distance, min_distance * 2, k, seeds=seed_bus_stops)):
        edge = busstop[2]
        dist_along = busstop[3]
        ET.SubElement(bus_stations, "busStation", attrib={
            "id": str(i),
            "edge": edge.getID(),
            "pos": str(dist_along),  # TODO check if this is the distance from the correct end
        })


def main():
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    setup_logging(args)

    # Parse random and seed arguments
    if not args["--random"]:
        random.seed(args["--seed"])
    # The 'noise' lib has good resolution until above 10 mil, but a SIGSEGV is had on values above [-100000, 100000]
    import perlin
    perlin.POPULATION_BASE = random.randint(0, 65_536)
    perlin.INDUSTRY_BASE = random.randint(0, 65_536)
    while perlin.POPULATION_BASE == perlin.INDUSTRY_BASE:
        perlin.INDUSTRY_BASE = random.randint(0, 65_536)
    logging.debug(f"Using POPULATION_BASE: {perlin.POPULATION_BASE}, INDUSTRY_BASE: {perlin.INDUSTRY_BASE}")

    # Read in SUMO network
    logging.info(f"Reading network from: {args['--net-file']}")
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    logging.info(f"Parsing stat file: {args['--stat-file']}")
    stats = ET.parse(args["--stat-file"])
    verify_stats(stats)

    logging.info("Writing Perlin noise to population and industry")
    centre = find_city_centre(net) if args["--centre.pos"] == "auto" else tuple(
        map(int, args["--centre.pos"].split(",")))

    # Populate network with street data
    logging.debug(f"Using centre: {centre}, "
                  f"centre.pop-weight: {float(args['--centre.pop-weight'])}, "
                  f"centre.work-weight: {float(args['--centre.work-weight'])}")
    apply_network_noise(net, stats, centre, float(args["--centre.pop-weight"]), float(args["--centre.work-weight"]))

    logging.info(f"Setting up {int(args['--gates.count'])} city gates")
    setup_city_gates(net, stats, int(args["--gates.count"]))

    logging.info("Setting up schools")
    setup_schools(args, net, stats, centre)

    logging.info(f"Setting up bus-stops")
    setup_bus_stops(net, stats, int(args["--bus-stop.distance"]), int(args["--bus-stop.k"]))

    # Write statistics back
    logging.info(f"Writing statistics file to {args['--output-file']}")
    stats.write(args["--output-file"])

    if args["--display"]:
        max_size = int(args["--display.size"])
        logging.info(f"Displaying network as image of max size {max_size}x{max_size}")
        display_network(net, stats, max_size, centre, args["--net-file"])


if __name__ == "__main__":
    main()
