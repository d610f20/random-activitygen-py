import os
import sys
from pathlib import Path
from pprint import pprint
from sys import stderr

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import xml.etree.ElementTree as ET

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


class TestInstance:
    def __init__(self, name: str, net_file: str, gen_stats_file: str, real_stats_file: str):
        self.name = name
        self.net_file = net_file
        self.gen_stats_file = gen_stats_file
        self.real_stats_file = real_stats_file

        try:
            Path(self.net_file).resolve(strict=True)
            Path(self.gen_stats_file).resolve(strict=True)
            Path(self.real_stats_file).resolve(strict=True)
        except FileNotFoundError:
            print(f"Files for test instance: {self.name} does not exist", file=stderr)
            exit(1)


test_instances = [
    TestInstance("Esbjerg", "in/cities/esbjerg.net.xml", "out/cities/esbjerg.stat.xml", "stats/esbjerg.stat.xml"),
    TestInstance("Slagelse", "in/cities/slagelse.net.xml", "out/cities/slagelse.stat.xml", "stats/slagelse.stat.xml")
]


def main():
    test = test_instances[0]

    net = sumolib.net.readNet(test.net_file)
    gen_stats = ET.parse(test.gen_stats_file)
    real_stats = ET.parse(test.real_stats_file)

    # Get mean school coordinates for real and generated statistics
    gen_mean_school_coords = get_mean_coords([net.getEdge(xml_school.get("edge")).getShape() for xml_school in
                                              gen_stats.find("schools").findall("school")])
    real_mean_school_coords = get_mean_coords([net.getEdge(xml_school.get("edge")).getShape() for xml_school in
                                               real_stats.find("schools").findall("school")])

    # Map each school in both sets to each other by shortest respective distance
    # Note leftover schools are ignored in either set
    # https://stackoverflow.com/questions/39016821/minimize-total-distance-between-two-sets-of-points-in-python
    dist = cdist(gen_mean_school_coords, real_mean_school_coords)
    row, col = linear_sum_assignment(dist)

    total_cost = dist[row, col].sum()
    print(total_cost)

    school_cost = [dist[i, col[i]] for i in row]
    pprint(school_cost)
    pprint(np.mean(school_cost))
    # Calculate mean distance between schools in both sets

    # FIXME: Hypothesis, schools are not placed worse than 2km from real ones on average


def get_mean_coords(schools: list):
    # Get centre of each school edge coordinate
    normalised_coords = []
    for school in schools:
        x, y = [], []
        for coords in school:
            x.append(coords[0])
            y.append(coords[1])
        normalised_coords.append((np.mean(x), np.mean(y)))
    return normalised_coords


def test():
    np.random.seed(100)

    points1 = np.array([(x, y) for x in np.linspace(-1, 1, 7) for y in np.linspace(-1, 1, 7)])
    N = points1.shape[0]
    points2 = 2 * np.random.rand(N, 2) - 1

    C = cdist(points1, points2)

    _, assigment = linear_sum_assignment(C)

    plt.plot(points1[:, 0], points1[:, 1], 'bo', markersize=10)
    plt.plot(points2[:, 0], points2[:, 1], 'rs', markersize=7)
    for p in range(N):
        plt.plot([points1[p, 0], points2[assigment[p], 0]], [points1[p, 1], points2[assigment[p], 1]], 'k')
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)
    plt.show()
    # plt.axes().set_aspect('equal')


if __name__ == '__main__':
    main()
    # test()
