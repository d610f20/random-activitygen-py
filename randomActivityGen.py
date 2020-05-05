"""Usage:
    randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--centre.pos=args]
    [--centre.pop-weight=F] [--centre.work-weight=F] [--gates.count=N] [--schools.stepsize=F] [--schools.open=args]
    [--schools.close=args]  [--primary-school.begin-age=args] [--primary-school.end-age=args] [--primary-school.count=N]
    [--primary-school.ratio=F] [--primary-school.capacity=args] [--high-school.begin-age=args]
    [--high-school.end-age=args] [--high-school.count=N] [--high-school.ratio=F] [--high-school.capacity=args]
    [--college.begin-age=args] [--college.end-age=args] [--college.count=N] [--college.ratio=F]
    [--college.capacity=args] [--bus-stop] [--bus-stop.distance=N] [--bus-stop.k=N] [--display] [--display.size=N]
    [--seed=S | --random] ([--quiet] | [--verbose] | [--log-level=LEVEL]) [--log-file=FILENAME]
    randomActivityGen.py --net-file=FILE --stat-file=FILE [--output-file=FILE] --display-only

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    --centre.pos args           The coordinates for the city's centre, e.g. "300,500" or "auto" [default: auto]
    --centre.pop-weight F       The increase in population near the city center [default: 0.5]
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
    --bus-stop                  Do experimental bus-stop generation
    --bus-stop.distance N       Minimum distance between bus stops [default: 500]
    --bus-stop.k N              Placement attempts in the poisson-disc algorithm [default: 10]
    --display                   Displays an image of city elements and the noise used to generate them.
    --display.size N            Set max width and height of image to display to N [default: 800]
    --display-only              Displays an image of city elements from existing statistics file. If given uses --stat-file for input.
    --verbose                   Sets log-level to DEBUG
    --quiet                     Sets log-level to ERROR
    --log-level=<LEVEL>         Explicitly set log-level {DEBUG, INFO, WARN, ERROR, CRITICAL} [default: INFO]
    --log-file=<FILENAME>       Set log filename [default: randomActivityGen-log.txt]
    --seed S                    Initialises the random number generator with the given value S [default: 31415]
    --random                    Initialises the random number generator with the current system time [default: false]
    -h, --help                  Show this screen.
    --version                   Show version.
"""

import logging
import os
import random
import sys
import xml.etree.ElementTree as ET

from docopt import docopt

from bus import setup_bus_stops
from gates import setup_city_gates
from perlin import setup_streets, NoiseSampler
from render import display_network
from school import setup_schools
from utility import find_city_centre, verify_stats, setup_logging, radius_of_network

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def main():
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    setup_logging(args)

    # Parse random and seed arguments
    if not args["--random"]:
        random.seed(args["--seed"])
    pop_offset = 65_536 * random.random()
    work_offset = 65_536 * random.random()
    while pop_offset == work_offset:
        work_offset = 65_536 * random.random()
    logging.debug(f"[main] Using pop_offset: {pop_offset}, work_offset: {work_offset}")

    # Read in SUMO network
    logging.debug(f"[main] Reading network from: {args['--net-file']}")
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    logging.debug(f"[main] Parsing stat file: {args['--stat-file']}")
    stats = ET.parse(args["--stat-file"])
    verify_stats(stats)

    max_display_size = int(args["--display.size"])

    centre = find_city_centre(net) if args["--centre.pos"] == "auto" else tuple(map(int, args["--centre.pos"].split(",")))
    radius = radius_of_network(net, centre)

    # If display-only, load stat-file as input and exit after rendering
    if args["--display-only"]:
        # Try the output-file first, as, if given, it contains a computed statistics file, otherwise try the input
        stats = ET.parse(args["--output-file"] or args["--stat-file"])
        logging.debug(f"[main] Displaying network as image of max size {max_display_size}x{max_display_size}")
        display_network(net, stats, max_display_size, centre, args["--net-file"])
        exit(0)

    # Prepare noise sampling
    pop_noise = NoiseSampler(centre, float(args['--centre.pop-weight']), radius, pop_offset)
    work_noise = NoiseSampler(centre, float(args['--centre.work-weight']), radius, work_offset)

    logging.debug(f"[main] Using centre: {centre}, "
                  f"radius: {radius}, "
                  f"centre.pop-weight: {float(args['--centre.pop-weight'])}, "
                  f"centre.work-weight: {float(args['--centre.work-weight'])}")

    logging.info("Setting up streets with population and workplaces")
    setup_streets(net, stats, pop_noise, work_noise)

    logging.debug(f"[main] Setting up {int(args['--gates.count'])} city gates")
    setup_city_gates(net, stats, int(args["--gates.count"]))

    logging.info("Setting up schools")
    setup_schools(args, net, stats, pop_noise)

    if args["--bus-stop"]:
        logging.debug(f"[main] Setting up bus-stops")
        setup_bus_stops(net, stats, int(args["--bus-stop.distance"]), int(args["--bus-stop.k"]))

    # Write statistics back
    logging.debug(f"[main] Writing statistics file to {args['--output-file']}")
    stats.write(args["--output-file"])

    if args["--display"]:
        logging.debug(f"[main] Displaying network as image of max size {max_display_size}x{max_display_size}")
        display_network(net, stats, max_display_size, centre, args["--net-file"])


if __name__ == "__main__":
    main()
