import logging
import os
import random
import sys
import xml.etree.ElementTree as ET

from perlin import NoiseSampler, get_edge_pair_centroid
from utility import k_means_clusters

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def find_school_edges(net: sumolib.net.Net, num_schools: int, pop_noise: NoiseSampler):
    """
    Uses k-means clustering to partition network into number of clusters equal to number of schools to be placed.
    Finds the edge in each cluster that allows both pedestrians and passengers with highest perlin noise, and returns a
    list of all these
    :param num_schools: number of schools that should be placed in total
    :return: the edges schools
    should be placed on
    """
    # Use k-means, to split the net into num_schools number of clusters, each containing approx same number of edges
    districts = k_means_clusters(net, num_schools)

    school_edges = []

    def find_valid_edge(edges):
        for edge in edges:
            if edge.allows("pedestrian") and edge.allows("passenger"):
                return edge
        logging.debug(f"[school] Not able to find valid edge for school in cluster")

    # Sort each edge in each district based on their noise
    for district in districts:
        district.sort(key=lambda x: pop_noise.sample(get_edge_pair_centroid(x.getShape())))

        # Reverse list, so 0 index has the highest noise
        district.reverse()

        # Get the edge with highest noise, that also allows for both pedestrians, and passenger cars This is done to
        # avoid placing schools on highways (pedestrians not allowed) and also on small paths in forests,
        # parks and so on (passenger cars not allowed)
        valid_edge = (find_valid_edge(district))
        if valid_edge is not None:
            school_edges.append(valid_edge)

    return school_edges


def insert_schools(args, new_school_edges: list, stats: ET.ElementTree, school_type: str):
    """
    Inserts schools in the given stats file, with random fields within certain bounds, either given as a parameter
    from user, or from default values for the school_type
        :param new_school_edges: edges to place schools on
        :param stats: stats file to write to
        :param school_type: type of schools that are being placed, different school types have different bounds for random fields
    """
    school_open_earliest = int(args["--schools.open"].split(",")[0]) * 3600
    school_open_latest = int(args["--schools.open"].split(",")[1]) * 3600
    school_close_earliest = int(args["--schools.close"].split(",")[0]) * 3600
    school_close_latest = int(args["--schools.close"].split(",")[1]) * 3600
    school_stepsize = int((float(args["--schools.stepsize"]) * 3600))
    logging.debug(f"[school] For school generation using:\n\tschool_open_earliest:\t {school_open_earliest}\n\t"
                  f"school_open_latest:\t\t {school_open_latest}\n\t"
                  f"school_close_earliest:\t {school_close_earliest}\n\t"
                  f"school_close_latest:\t {school_close_latest}\n\t"
                  f"school_stepsize:\t\t {school_stepsize}")

    xml_schools = stats.find('schools')
    if xml_schools is None:
        xml_schools = ET.SubElement(stats.getroot(), "schools")

    # Insert schools, with semi-random parameters
    logging.debug(f"[school] Inserting {str(len(new_school_edges))} {school_type}(s)")
    for school_edge in new_school_edges:
        begin_age = random.randint(int(args[f"--{school_type}.begin-age"].split(",")[0]),
                                   int(args[f"--{school_type}.begin-age"].split(",")[1]))
        end_age = random.randint(int(args[f"--{school_type}.end-age"].split(",")[0]) if begin_age + 1 <= int(
            args[f"--{school_type}.end-age"].split(",")[0]) else begin_age + 1,
                                 int(args[f"--{school_type}.end-age"].split(",")[1]))
        logging.debug(f"[school] Using begin_age: {begin_age}, end_age: {end_age} for {school_type}(s)")

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


def get_school_count(args, stats: ET.ElementTree, school_type: str):
    """
    If no number is specified for a specific school type, the default ratio between population and school_type is
    used (school_type.ratio)  to calculate number of schools
    :return: the number of schools of a given school_type to be placed
    """
    if args[f"--{school_type}.count"] == "auto":
        schools_per_1000_inhabitants = float(args[f"--{school_type}.ratio"])

        # Calculate default number of schools, based on population if none input parameter
        xml_general = stats.find('general')
        inhabitants = xml_general.get('inhabitants')
        school_count = int(inhabitants) * schools_per_1000_inhabitants // 1000

    else:
        # Else place new number of schools as according to input
        school_count = int(args[f"--{school_type}.count"])

    return school_count


def setup_schools(args, net: sumolib.net.Net, stats: ET.ElementTree, pop_noise: NoiseSampler):
    """
    Removes all existing schools in stats file, finds total number of schools to be placed in the net, splits net
    into k-clusters, and then places a school on the edge with highest perlin noise in each cluster
    """
    xml_schools = stats.find('schools')
    # Remove all previous schools if any exists, effectively overwriting these
    if xml_schools is not None:
        schools = xml_schools.findall('school')
        for school in schools:
            xml_schools.remove(school)

    # Get number of schools to be placed
    primary_school_count = int(get_school_count(args, stats, "primary-school"))
    high_school_count = int(get_school_count(args, stats, "high-school"))
    college_count = int(get_school_count(args, stats, "college"))

    school_count = primary_school_count + high_school_count + college_count

    # Find edges to place schools on
    if 0 < school_count:
        new_school_edges = find_school_edges(net, school_count, pop_noise)

    # Place primary schools (if any) on the first edges in new_school_edges
    if 0 < primary_school_count:
        insert_schools(args, new_school_edges[:primary_school_count], stats, "primary-school")

    # Then place high schools (if any) on the next edges in new_school_edges
    if 0 < high_school_count:
        insert_schools(args, new_school_edges[primary_school_count:primary_school_count + high_school_count], stats,
                       "high-school")

    # Place colleges (if any) on the remaining edges in new_school_edges, as the remaining number of edges should
    # reflect number of colleges
    if 0 < college_count:
        insert_schools(args, new_school_edges[primary_school_count + high_school_count:school_count], stats, "college")
