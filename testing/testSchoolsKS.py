import csv
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from testing.testInstance import TestInstance, test_instances
from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def write_school_coords(net: sumolib.net.Net, stats: ET.ElementTree, filename):
    """
    Writes all schools' positions found in stats file to a csv called 'filename'. These coordinates can be used for
    testing, e.g 2d KS tests between generated schools, and real school positions in the city
    :param net: network file that the schools in stats file is placed on
    :param stats: stats file parsed with ElementTree containing schools :param filename: name of csv to be written
    """
    # Ensure that output directory exists
    directory = "school_coordinates"
    if not os.path.exists(directory):
        os.mkdir(directory)

    xml_schools = [xml_school for xml_school in stats.find("schools").findall("school")]

    if xml_schools is None:
        print(f"Cannot write schools to CSV: no schools found in the generated stats file for {filename}")
        return

    positions = []

    # find all generated school positions, append to positions
    for gen_school_edge in xml_schools:
        pos = float(gen_school_edge.get("pos"))
        edge = net.getEdge(gen_school_edge.get("edge"))
        positions.append(position_on_edge(edge, pos))

    # workaround to append columns to csv file. read old_csv, make a new csv and write to this, rename to old csv when done
    old_csv = f'{directory}/{filename}-school-coords.csv'
    new_csv = f'{directory}/{filename}-school-coords-new.csv'

    # if the old_csv already exists, do as mentioned above
    if os.path.exists(old_csv):
        with open(old_csv, 'r') as read_obj, \
                open(new_csv, 'w', newline='') as write_obj:
            csv_reader = csv.reader(read_obj)
            csv_writer = csv.writer(write_obj)
            for i, row in enumerate(csv_reader):
                row.append(positions[i][0])
                row.append(positions[i][1])
                csv_writer.writerow(row)
        try:
            os.rename(new_csv, old_csv)
        except WindowsError:
            os.remove(old_csv)
            os.rename(new_csv, old_csv)
    else:
        # if file does not exist, simply write to it
        file = open(old_csv, 'w', newline='')
        with file:
            writer = csv.writer(file)
            writer.writerows(positions)


def run_multiple_test(test: TestInstance, times: int):
    # find number of actual schools in the city
    real_schools_count = len(
        [xml_school for xml_school in ET.parse(test.real_stats_file).find("schools").findall("school")])

    # execute a test-instance n times
    for n in range(0, times):
        # run randomActivityGen with correct number of schools
        test.run_tool(real_schools_count)

        write_school_coords(sumolib.net.readNet(test.net_file), ET.parse(f"../out/{test.name}.stat.xml"), test.name)


if __name__ == '__main__':
    runs_per_city = 5
    [run_multiple_test(test, runs_per_city) for test in test_instances]
