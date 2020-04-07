"""Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--centre.pos=args]
    [--centre.pop-weight=F] [--centre.work-weight=F] [--gates.count=N] [--schools.count=N] [--schools.ratio=F]
    [--schools.stepsize=F] [--schools.open=args] [--schools.close=args]  [--schools.begin-age=args]
    [--schools.end-age=args] [--schools.capacity=args] [--bus-stop.distance=N] [--bus-stop.k=N] [--display] [--seed=S | --random]
    ([--quiet] | [--verbose] | [--log-level=LEVEL]) [--log-file=FILENAME]

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
    --schools.count N           Number of schools in the city, if not used, number of schools is based on population [default: auto]
    --schools.ratio F           Number of schools per 1000 inhabitants [default: 0.2]
    --schools.stepsize F        Stepsize in opening/closing hours, in parts of an hour, e.g 0.25 is every 15 mins [default: 0.25]
    --schools.open=args         The interval at which the schools opens (24h clock) [default: 7,10]
    --schools.close=args        The interval at which the schools closes (24h clock) [default: 13,17]
    --schools.begin-age=args    The range of ages at which students start going to school [default: 6,20]
    --schools.end-age=args      The range of ages at which students stops going to school [default: 10,30]
    --schools.capacity=args     The range for capacity in schools [default: 100,500]
    --bus-stop.distance N       Minimum distance between bus stops [default: 500]
    --bus-stop.k N              Placement attempts in the poisson-disc algorithm [default: 10]
    --display                   Displays an image of cities elements and the noise used to generate them.
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

            for edge in edges:
                if edge.getID() == edge_id:
                    pos = position_on_edge(edge, along)

                    seed_bus_stops.append([
                        pos[0],
                        pos[1],
                        edge,
                        along])
                    break
            else:
                print("[warning] BusStation in stat file reference edge that doesn't exist in the road network")
        assert isinstance(seed_bus_stops, list)

    for i, busstop in enumerate(bus_stop_generator(edges, min_distance, min_distance*2, k, seeds=seed_bus_stops)):
        edge = busstop[2]
        dist_along = busstop[3]
        print("along:", dist_along, i, edge.getID())
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

    logging.info(f"Setting up {int(args['--gates.count'])} city gates ")
    setup_city_gates(net, stats, int(args["--gates.count"]))

    if args["--schools.count"] == "auto":
        logging.info("Setting up schools automatically")
        setup_schools(args, net, stats, None, centre)
    else:
        logging.info(f"Setting up {int(args['--schools.count'])} schools")
        setup_schools(args, net, stats, int(args["--schools.count"]), centre)

    setup_bus_stops(net, stats, int(args["--bus-stop.distance"]), int(args["--bus-stop.k"]))

    # Write statistics back
    logging.info(f"Writing statistics file to {args['--output-file']}")
    stats.write(args["--output-file"])

    if args["--display"]:
        x_max_size, y_max_size = 500, 500
        logging.info(f"Displaying network as image of max: {x_max_size} x {y_max_size} dimensions")
        display_network(net, stats, x_max_size, y_max_size)


if __name__ == "__main__":
    main()
