import csv
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from pprint import pprint
from sys import stderr

from utility import position_on_edge

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


class TestInstance:
    def __init__(self, name: str, net_file: str, gen_stats_in_file: str, real_stats_file: str, centre):
        self.name = name
        self.centre = centre
        self.net_file = net_file
        self.gen_stats_in_file = gen_stats_in_file
        self.real_stats_file = real_stats_file

        try:
            Path(self.net_file).resolve(strict=True)
            Path(self.gen_stats_in_file).resolve(strict=True)
            Path(self.real_stats_file).resolve(strict=True)
        except FileNotFoundError:
            print(f"Files for test instance: {self.name} does not exist", file=stderr)
            pprint(self.__dict__)
            exit(1)


test_instances = [
    TestInstance("aalborg", "../in/cities/aalborg.net.xml", "../in/cities/aalborg.stat.xml",
                 "../stats/aalborg.stat.xml", "9396,12766"),
    TestInstance("esbjerg", "../in/cities/esbjerg.net.xml", "../in/cities/esbjerg.stat.xml",
                 "../stats/esbjerg.stat.xml", "7476,1712"),
    TestInstance("randers", "../in/cities/randers.net.xml", "../in/cities/randers.stat.xml",
                 "../stats/randers.stat.xml", "19516,6606"),
    TestInstance("slagelse", "../in/cities/slagelse.net.xml", "../in/cities/slagelse.stat.xml",
                 "../stats/slagelse.stat.xml", "6073,4445"),
    TestInstance("vejen", "../in/cities/vejen.net.xml", "../in/cities/vejen.stat.xml", "../stats/vejen.stat.xml",
                 "37800,3790")
]


def write_school_coords(net: sumolib.net.Net, stats: ET.ElementTree, filename):
    """
    Writes all schools' positions found in stats file to a csv called 'filename'. These coordinates can be used for
    testing, e.g 2d KS tests between generated schools, and real school positions in the city
    :param net: network file that the schools in stats file is placed on :param stats: stats
    file parsed with ElementTree containing schools :param filename: name of csv to be written
    """
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
    old_csv = f'../out/{filename}.csv'
    new_csv = f'../out/{filename}-new.csv'

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
        subprocess.run(
            ["python", "../randomActivityGen.py", f"--net-file={test.net_file}",
             f"--stat-file={test.gen_stats_in_file}", f"--centre.pos={test.centre}",
             f"--output-file=../out/{test.name}.stat.xml", "--quiet",
             f"--random",
             f"--primary-school.count=0", f"--high-school.count=0", f"--college.count={real_schools_count}"])

        write_school_coords(sumolib.net.readNet(test.net_file), ET.parse(f"../out/{test.name}.stat.xml"), test.name)


if __name__ == '__main__':
    runs_per_city = 5
    [run_multiple_test(test, runs_per_city) for test in test_instances]
