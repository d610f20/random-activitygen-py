import math
import random
import xml.etree.ElementTree as ET
import os
import sys
import logging

from typing import Tuple
from perlin import POPULATION_BASE, sample_edge_noise
from utility import find_city_centre, radius_of_network, k_means_clusters

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
    centre = find_city_centre(net)
    radius = radius_of_network(net, centre)
    # Sort each edge in each district based on their noise, and return edge with highest noise from each district
    for district in districts:
        district.sort(key=lambda x: sample_edge_noise(x, centre=centre, radius=radius, base=POPULATION_BASE))
        school_edges.append(district[-1])

    return school_edges


def setup_primary_schools(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float]):
    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")
    if args["--primary-schools.count"] == "auto":
        # Voodoo parameter, seems to be about the value for a couple of danish cities.
        # In general one high school, per 5000-7000 inhabitant in a city, so 0.2 pr 1000 inhabitants
        schools_per_1000_inhabitants = float(args["--primary-schools.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        num_schools_default = math.ceil(int(inhabitants) * schools_per_1000_inhabitants / 1000)

        # Number of new schools to be placed
        number_new_schools = num_schools_default - len(xml_schools.findall("school"))
    else:
        # Else place new number of schools as according to input
        school_count = int(args["--primary-schools.count"])
        number_new_schools = school_count - len(xml_schools.findall("school"))

        if number_new_schools <= 0:
            logging.warning(f"{school_count} schools was requested, but there are already {len(xml_schools)} defined")
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
    logging.info("Inserting " + str(len(new_school_edges)) + " new primary school(s)")
    for school_edge in new_school_edges:
        begin_age = random.randint(int(args["--primary-schools.begin-age"].split(",")[0]),
                                   int(args["--primary-schools.begin-age"].split(",")[1]))
        end_age = random.randint(int(args["--primary-schools.end-age"].split(",")[0]) if begin_age + 1 <= int(
            args["--primary-schools.end-age"].split(",")[0]) else begin_age + 1,
                                 int(args["--primary-schools.end-age"].split(",")[1]))
        logging.debug(f"Using begin_age: {begin_age}, end_age: {end_age} for school(s)")

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school_edge.getID()),
            "pos": str(random.randint(0, int(school_edge.getLength()))),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(int(args["--primary-schools.capacity"].split(",")[0]),
                                           int(args["--primary-schools.capacity"].split(",")[1]))),
            "opening": str(random.randrange(school_open_earliest, school_open_latest, school_stepsize)),
            "closing": str(random.randrange(school_close_earliest, school_close_latest, school_stepsize))
        })


def setup_high_schools(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float]):
    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")
    if args["--high-schools.count"] == "auto":
        # Voodoo parameter, seems to be about the value for a couple of danish cities.
        # In general one high school, per 25-35k inhabitant in a city, so 0.04 pr 1000 inhabitants
        schools_per_1000_inhabitants = float(args["--high-schools.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        school_count = math.ceil(int(inhabitants) * schools_per_1000_inhabitants / 1000)
    else:
        # Else place new number of schools as according to input
        school_count = int(args["--high-schools.count"])

        if school_count <= 0:
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
    new_school_edges = find_school_edges(net, school_count, centre)

    # Insert schools, with semi-random parameters
    logging.info("Inserting " + str(len(new_school_edges)) + " new high school(s)")
    for school_edge in new_school_edges:
        begin_age = random.randint(int(args["--high-schools.begin-age"].split(",")[0]),
                                   int(args["--high-schools.begin-age"].split(",")[1]))
        end_age = random.randint(int(args["--high-schools.end-age"].split(",")[0]) if begin_age + 1 <= int(
            args["--high-schools.end-age"].split(",")[0]) else begin_age + 1,
                                 int(args["--high-schools.end-age"].split(",")[1]))
        logging.debug(f"Using begin_age: {begin_age}, end_age: {end_age} for school(s)")

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school_edge.getID()),
            "pos": str(random.randint(0, int(school_edge.getLength()))),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(int(args["--high-schools.capacity"].split(",")[0]),
                                           int(args["--high-schools.capacity"].split(",")[1]))),
            "opening": str(random.randrange(school_open_earliest, school_open_latest, school_stepsize)),
            "closing": str(random.randrange(school_close_earliest, school_close_latest, school_stepsize))
        })


def setup_colleges(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float]):
    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")
    if args["--colleges.count"] == "auto":
        # Voodoo parameter, seems to be about the value for a couple of danish cities.
        # In general one high school, per 25-35k inhabitant in a city, so 0.04 pr 1000 inhabitants
        schools_per_1000_inhabitants = float(args["--colleges.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        school_count = math.ceil(int(inhabitants) * schools_per_1000_inhabitants / 1000)
    else:
        # Else place new number of schools as according to input
        school_count = int(args["--colleges.count"])

        if school_count <= 0:
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
    new_school_edges = find_school_edges(net, school_count, centre)

    # Insert schools, with semi-random parameters
    logging.info("Inserting " + str(len(new_school_edges)) + " new college(s)")
    for school_edge in new_school_edges:
        begin_age = random.randint(int(args["--colleges.begin-age"].split(",")[0]),
                                   int(args["--colleges.begin-age"].split(",")[1]))
        end_age = random.randint(int(args["--colleges.end-age"].split(",")[0]) if begin_age + 1 <= int(
            args["--colleges.end-age"].split(",")[0]) else begin_age + 1,
                                 int(args["--colleges.end-age"].split(",")[1]))
        logging.debug(f"Using begin_age: {begin_age}, end_age: {end_age} for school(s)")

        ET.SubElement(xml_schools, "school", attrib={
            "edge": str(school_edge.getID()),
            "pos": str(random.randint(0, int(school_edge.getLength()))),
            "beginAge": str(begin_age),
            "endAge": str(end_age),
            "capacity": str(random.randint(int(args["--colleges.capacity"].split(",")[0]),
                                           int(args["--colleges.capacity"].split(",")[1]))),
            "opening": str(random.randrange(school_open_earliest, school_open_latest, school_stepsize)),
            "closing": str(random.randrange(school_close_earliest, school_close_latest, school_stepsize))
        })


def setup_schools(args, net: sumolib.net.Net, stats: ET.ElementTree, centre: Tuple[float, float]):
    setup_primary_schools(args, net, stats, centre)
    setup_high_schools(args, net, stats, centre)
    setup_colleges(args, net, stats, centre)
