import math
import random
import xml.etree.ElementTree as ET
import os
import sys
import logging

from typing import Tuple
from perlin import POPULATION_BASE, sample_edge_noise
from utility import radius_of_network, k_means_clusters

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_school_edges(net: sumolib.net.Net, num_schools: int, centre: Tuple[float, float]):
    # Use k-means, to split the net into num_schools number of clusters, each containing approx same number of edges
    districts = k_means_clusters(net, num_schools)

    school_edges = []
    radius = radius_of_network(net, centre)
    # Sort each edge in each district based on their noise, and return edge with highest noise from each district
    for district in districts:
        district.sort(key=lambda x: sample_edge_noise(x, centre=centre, radius=radius, base=POPULATION_BASE))
        school_edges.append(district[-1])

    return school_edges


def insert_schools(args, new_school_edges, stats, school_type):
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

    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")

    # Insert schools, with semi-random parameters
    logging.info("Inserting " + str(len(new_school_edges)) + f" new {school_type}(s)")
    for school_edge in new_school_edges:
        begin_age = random.randint(int(args[f"--{school_type}.begin-age"].split(",")[0]),
                                   int(args[f"--{school_type}.begin-age"].split(",")[1]))
        end_age = random.randint(int(args[f"--{school_type}.end-age"].split(",")[0]) if begin_age + 1 <= int(
            args[f"--{school_type}.end-age"].split(",")[0]) else begin_age + 1,
                                 int(args[f"--{school_type}.end-age"].split(",")[1]))
        logging.debug(f"Using begin_age: {begin_age}, end_age: {end_age} for {school_type}(s)")

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school_edge.getID()),
            "pos": str(random.randint(0, int(school_edge.getLength()))),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(int(args[f"--{school_type}.capacity"].split(",")[0]),
                                           int(args[f"--{school_type}.capacity"].split(",")[1]))),
            "opening": str(random.randrange(school_open_earliest, school_open_latest, school_stepsize)),
            "closing": str(random.randrange(school_close_earliest, school_close_latest, school_stepsize))
        })


def get_school_count(args, stats, school_type):
    if args[f"--{school_type}.count"] == "auto":
        # Voodoo parameter, seems to be about the value for a couple of danish cities.
        # In general one high school, per 5000-7000 inhabitant in a city, so 0.2 pr 1000 inhabitants
        schools_per_1000_inhabitants = float(args[f"--{school_type}.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        school_count = math.ceil(int(inhabitants) * schools_per_1000_inhabitants / 1000)

    else:
        # Else place new number of schools as according to input
        school_count = int(args[f"--{school_type}.count"])

    return school_count


def setup_type_of_school(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float], school_type):
    # Get number of primary schools to be placed
    school_count = get_school_count(args, stats, school_type)

    # Find edges to place schools on
    new_school_edges = find_school_edges(net, school_count, centre)

    # Insert schools on edges found
    insert_schools(args, new_school_edges, stats, school_type)


def setup_schools(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float]):
    setup_type_of_school(args, net, stats, centre, "primary-schools")
    setup_type_of_school(args, net, stats, centre, "high-schools")
    setup_type_of_school(args, net, stats, centre, "colleges")
