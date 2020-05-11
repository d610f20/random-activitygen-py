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
    def __init__(self, name: str, net_file: str, gen_stats_in_file: str, gen_stats_out_file: str, real_stats_file: str):
        self.name = name
        self.net_file = net_file
        self.gen_stats_in_file = gen_stats_in_file
        self.gen_stats_out_file = gen_stats_out_file
        self.real_stats_file = real_stats_file

        try:
            Path(self.net_file).resolve(strict=True)
            Path(self.gen_stats_in_file).resolve(strict=True)
            Path(self.gen_stats_out_file).resolve(strict=True)
            Path(self.real_stats_file).resolve(strict=True)
        except FileNotFoundError:
            print(f"Files for test instance: {self.name} does not exist", file=stderr)
            pprint(self.__dict__)
            exit(1)


test_instances = [
    '''TestInstance("esbjerg", "in/cities/esbjerg.net.xml", "in/cities/esbjerg.stat.xml", "out/cities/esbjerg.stat.xml",
                 "stats/esbjerg.stat.xml"),
    TestInstance("slagelse", "in/cities/slagelse.net.xml", "in/cities/slagelse.stat.xml",
                 "out/cities/slagelse.stat.xml", "stats/slagelse.stat.xml"),
    TestInstance("randers", "in/cities/randers.net.xml", "in/cities/randers.stat.xml", "out/cities/randers.stat.xml",
                 "stats/randers.stat.xml")''',
    TestInstance("vejen", "in/cities/vejen.net.xml", "in/cities/vejen.stat.xml", "out/cities/vejen.stat.xml",
                 "stats/vejen.stat.xml")
    # TestInstance("aalborg", "in/cities/aalborg.net.xml", "in/cities/aalborg.stat.xml", "out/cities/aalborg.stat.xml",
    #            "stats/aalborg.stat.xml")
]


def write_all_school_coords(net, city_name):
    write_school_coords(net, ET.parse(f"out\{city_name}.stat.xml"), f"out\{city_name}-generated-schools-pos.stat.xml")
    write_school_coords(net, ET.parse(f"stats\{city_name}.stat.xml"), f"out\{city_name}-real-schools-pos.stat.xml")


def write_school_coords(net: sumolib.net.Net, stats: ET.ElementTree, filename):
    xml_schools = [xml_school for xml_school in stats.find("schools").findall("school")]

    positions = []

    for gen_school_edge in xml_schools:
        pos = float(gen_school_edge.get("pos"))
        edge = net.getEdge(gen_school_edge.get("edge"))
        positions.append(position_on_edge(edge, pos))

    file = open(f'{filename}.csv', 'w')
    with file:
        writer = csv.writer(file)
        writer.writerows(positions)


def run_multiple_test(test: TestInstance, times: int):
    # execute a test-instance n times
    for n in range(0, times):
        # run main

        real_schools = len(
            [xml_school for xml_school in ET.parse(test.real_stats_file).find("schools").findall("school")])

        subprocess.run(
            ["python", "./randomActivityGen.py", f"--net-file={test.net_file}", f"--stat-file={test.gen_stats_in_file}",
             f"--output-file={test.gen_stats_out_file}", "--quiet", f"--random",
             f"--primary-school.count={real_schools}", f"--high-school.count=0", f"--college.count=0"])
        write_school_coords(test.net_file, test.gen_stats_out_file, test.name)


if __name__ == '__main__':
    [run_multiple_test(test, 10) for test in test_instances]  # Multiple runs per test
