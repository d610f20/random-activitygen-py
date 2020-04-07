"""Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--centre.pos=args]
    [--centre.pop-weight=F] [--centre.work-weight=F] [--gates.count=N] [--schools.count=N] [--schools.ratio=F]
    [--schools.stepsize=F] [--schools.open=args] [--schools.close=args]  [--schools.begin-age=args]
    [--schools.end-age=args] [--schools.capacity=args] [--display] [--seed=S | --random]
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
import math
import os
import random
import sys
import xml.etree.ElementTree as ET

import logging
from typing import Tuple

import numpy as np
from docopt import docopt

from perlin import apply_network_noise, get_edge_pair_centroid, POPULATION_BASE, get_population_number
from utility import find_city_centre, radius_of_network, verify_stats, setup_city_gates
from render import display_network

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_school_edges(net: sumolib.net.Net, num_schools: int, centre: Tuple[float, float]):
    edges = net.getEdges()

    # Sort all edges based on their avg coord
    edges.sort(key=lambda x: np.mean(get_edge_pair_centroid(x.getShape())))

    # Split edges into n districts, with n being number of schools
    district_size = int(np.ceil(len(edges) / num_schools))
    districts = [edges[x:x + district_size] for x in range(0, len(edges), district_size)]

    # Pick out the one edge with highest perlin noise from each district and return these to later place school on
    school_edges = []
    radius = radius_of_network(net, centre)
    for district in districts:
        district.sort(key=lambda x: get_population_number(x, centre=centre, radius=radius, base=POPULATION_BASE))
        school_edges.append(district[-1])

    return school_edges


def setup_schools(net: sumolib.net.Net, stats: ET.ElementTree, school_count: int or None, centre: Tuple[float, float]):
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")
    if school_count is None:
        # Voodoo parameter, seems to be about the value for a couple of danish cities.
        # In general one high school, per 5000-7000 inhabitant in a city, so 0.2 pr 1000 inhabitants
        schools_per_1000_inhabitants = float(args["--schools.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        num_schools_default = math.ceil(int(inhabitants) * schools_per_1000_inhabitants / 1000)

        # Number of new schools to be placed
        number_new_schools = num_schools_default - len(xml_schools.findall("school"))
    else:
        # Else place new number of schools as according to input
        number_new_schools = school_count - len(xml_schools.findall("school"))

    if number_new_schools == 0:
        return
    if number_new_schools < 0:
        print(f"Warning: {school_count} schools was requested, but there are already {len(xml_schools)} defined")
        return

    school_open_earliest = int(args["--schools.open"].split(",")[0]) * 3600
    school_open_latest = int(args["--schools.open"].split(",")[1]) * 3600
    school_close_earliest = int(args["--schools.close"].split(",")[0]) * 3600
    school_close_latest = int(args["--schools.close"].split(",")[1]) * 3600
    school_stepsize = int((float(args["--schools.stepsize"]) * 3600))
    logging.debug(f"For school generation using:\n\tschool_open_earliest:\t {school_open_earliest}\n\t"
                  f"school_open_latest:\t\t {school_open_latest}\n\t"
                  f"school_close_earliest:\t {school_close_earliest}\n\t"
                  f"school_close_latest:\t {school_close_latest}\n\t"
                  f"school_stepsize:\t\t {school_stepsize}")

    # Find edges to place schools on
    new_school_edges = find_school_edges(net, number_new_schools, centre)

    # Insert schools, with semi-random parameters
    logging.info("Inserting " + str(len(new_school_edges)) + " new school(s)")
    for school in new_school_edges:
        begin_age = random.randint(int(args["--schools.begin-age"].split(",")[0]),
                                   int(args["--schools.begin-age"].split(",")[1]))
        end_age = random.randint(int(args["--schools.end-age"].split(",")[1]) if begin_age + 1 <= int(
            args["--schools.end-age"].split(",")[1]) else begin_age + 1,
                                 int(args["--schools.end-age"].split(",")[1]))
        logging.debug(f"Using begin_age: {begin_age}, end_age: {end_age} for school(s)")

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school.getID()),
            "pos": str(random.randint(0, 100)),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(int(args["--schools.capacity"].split(",")[0]),
                                           int(args["--schools.capacity"].split(",")[1]))),
            "opening": str(random.randrange(school_open_earliest, school_open_latest, school_stepsize)),
            "closing": str(random.randrange(school_close_earliest, school_close_latest, school_stepsize))
        })


def main():
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    # Setup logging
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

    # FIXME: logfile should always print in DEBUG, this seems like a larger hurdle:
    # https://stackoverflow.com/questions/25187083/python-logging-to-multiple-handlers-at-different-log-levels
    log_file_handler.setLevel(logging.DEBUG)
    logger.addHandler(log_file_handler)

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
        setup_schools(net, stats, None, centre)
    else:
        logging.info(f"Setting up {int(args['--schools.count'])} schools")
        setup_schools(net, stats, int(args["--schools.count"]), centre)

    # Write statistics back
    logging.info(f"Writing statistics file to {args['--output-file']}")
    stats.write(args["--output-file"])

    if args["--display"]:
        x_max_size, y_max_size = 500, 500
        logging.info(f"Displaying network as image of max: {x_max_size} x {y_max_size} dimensions")
        display_network(net, stats, x_max_size, y_max_size, centre)


if __name__ == "__main__":
    main()
