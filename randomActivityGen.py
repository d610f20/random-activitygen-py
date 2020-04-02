"""
Usage: randomActivityGen.py --net-file=FILE --stat-file=FILE --output-file=FILE [--gates.count=N] [--schools.count=H]

Input Options:
    -n, --net-file FILE         Input road network file to create activity for
    -s, --stat-file FILE        Input statistics file to modify

Output Options:
    -o, --output-file FILE      Write modified statistics to FILE

Other Options:
    --gates.count N             Number of city gates in the city [default: 4]
    --schools.count H           Number of schools in the city, if not used, number of schools is based on population [default: population-based]
    -h, --help                  Show this screen.
    --version                   Show version.
"""
import math
import os
import random
import sys
import xml.etree.ElementTree as ET

import numpy as np
from docopt import docopt

from perlin import apply_network_noise, get_perlin_noise, get_edge_pair_centroid, POPULATION_BASE

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
        print(f"Warning: {gate_count} city gate was requested, but there are already {len(xml_entrances)} defined")
    if n <= 0:
        return
    print(f"Inserting {n} new city gates")

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
        ET.SubElement(xml_gates, "entrance", attrib={
            "edge": edge.getID(),
            "incoming": str(incoming_traffic),
            "outgoing": str(outgoing_traffic),
            "pos": "0"
        })


def find_school_edges(net: sumolib.net.Net, num_schools):
    edges = net.getEdges()

    # Sort all edges based on their avg coord
    edges.sort(key=lambda x: np.mean(get_edge_pair_centroid(x.getShape())))

    # Split edges into n districts, with n being number of schools
    district_size = int(np.ceil(len(edges) / num_schools))
    districts = [edges[x:x + district_size] for x in range(0, len(edges), district_size)]

    school_edges = []

    def noise(edge):
        x, y = get_edge_pair_centroid(edge.getShape())
        return get_perlin_noise(x, y, POPULATION_BASE)

    # Pick out the one edge with highest perlin noise from each district and return these to later place school on
    for district in districts:
        district.sort(key=noise)
        school_edges.append(district[-1])

    return school_edges


def setup_schools(net: sumolib.net.Net, stats: ET.ElementTree, school_count: int or None):
    # Voodoo parameter, seems to be about the value for a couple of danish cities.
    # In general one high school, per 5000-7000 inhabitant in a city
    inhabitants_per_school = 5000

    school_opening_earliest = 7 * 3600
    school_opening_latest = 10 * 3600
    school_closing_earliest = 13 * 3600
    school_closing_latest = 17 * 3600
    stepsize = int(0.25 * 3600)

    # Creates a list of school start times, in seconds. Ranges from 7am to 10am, with 15min intervals
    school_start_times = list(range(school_opening_earliest, school_opening_latest, stepsize))

    # Creates a list of school end times, in seconds. Ranges from 13pm to 17pm, with 15min intervals
    school_end_times = list(range(school_closing_earliest, school_closing_latest, stepsize))

    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")
    if school_count is None:
        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        num_schools_default = math.ceil(int(inhabitants) / inhabitants_per_school)

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

    # Find edges to place schools on
    new_school_edges = find_school_edges(net, number_new_schools)

    # Insert schools, with semi-random parameters
    print("Inserting " + str(len(new_school_edges)) + " new schools")
    for school in new_school_edges:
        begin_age = random.choice(list(range(6, 19)))
        end_age = random.choice(list(range(begin_age + 1, 26)))

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school.getID()),
            "pos": str(random.randint(0, 100)),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(100, 500)),
            "opening": str(random.choice(school_start_times)),
            "closing": str(random.choice(school_end_times))
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
        population = ET.SubElement(city, "population")
        ET.SubElement(population, "bracket", {"beginAge": "0", "endAge": "30", "peopleNbr": "30"})
        ET.SubElement(population, "bracket", {"beginAge": "30", "endAge": "60", "peopleNbr": "40"})
        ET.SubElement(population, "bracket", {"beginAge": "60", "endAge": "90", "peopleNbr": "30"})

    # Similarly at least and one opening and closing workhour is required
    work_hours = city.find("workHours")
    if work_hours is None:
        # Work hours are missing, so we add some default work hours
        work_hours = ET.SubElement(city, "workHours")
        ET.SubElement(work_hours, "opening", {"hour": "28800", "proportion": "70"})  # 70% at 8.00
        ET.SubElement(work_hours, "opening", {"hour": "30600", "proportion": "30"})  # 30% at 8.30
        ET.SubElement(work_hours, "closing", {"hour": "43200", "proportion": "10"})  # 10% at 12.00
        ET.SubElement(work_hours, "closing", {"hour": "61200", "proportion": "30"})  # 30% at 17.00
        ET.SubElement(work_hours, "closing", {"hour": "63000", "proportion": "60"})  # 60% at 17.30


def main():
    args = docopt(__doc__, version="RandomActivityGen v0.1")

    # Read in SUMO network
    net = sumolib.net.readNet(args["--net-file"])

    # Parse statistics configuration
    stats = ET.parse(args["--stat-file"])
    verify_stats(stats)

    # Scale and octave seems like sane values for the moment
    apply_network_noise(net, stats, 0.005, 3)

    setup_city_gates(net, stats, int(args["--gates.count"]))

    if args["--schools.count"] == "population-based":
        setup_schools(net, stats, None)
    else:
        setup_schools(net, stats, int(args["--schools.count"]))

    # Write statistics back
    stats.write(args["--output-file"])


if __name__ == "__main__":
    main()
