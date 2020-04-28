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


# TODO; maybe do image drawing like test() og gen vs real school placement over network, if extra time


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
            pprint(self.__dict__)
            exit(1)


test_instances = [
    TestInstance("Esbjerg", "in/cities/esbjerg.net.xml", "out/cities/esbjerg.stat.xml", "stats/esbjerg.stat.xml"),
    TestInstance("Slagelse", "in/cities/slagelse.net.xml", "out/cities/slagelse.stat.xml", "stats/slagelse.stat.xml"),
    TestInstance("Randers", "in/cities/randers.net.xml", "out/cities/randers.stat.xml", "stats/randers.stat.xml"),
    TestInstance("Vejen", "in/cities/vejen.net.xml", "out/cities/vejen.stat.xml", "stats/vejen.stat.xml"),
    TestInstance("Aalborg", "in/cities/aalborg.net.xml", "out/cities/aalborg.stat.xml", "stats/aalborg.stat.xml")
]


def calc_school_divergence(test: TestInstance, plot: bool):
    net = sumolib.net.readNet(test.net_file)

    # Get mean school coordinates for real and generated statistics
    gen_coords = np.array(get_mean_coords([net.getEdge(xml_school.get("edge")).getShape() for xml_school in
                                           ET.parse(test.gen_stats_file).find("schools").findall("school")]))
    real_coords = np.array(get_mean_coords([net.getEdge(xml_school.get("edge")).getShape() for xml_school in
                                            ET.parse(test.real_stats_file).find("schools").findall("school")]))

    # Get euclidean distance between all points in both sets as a cost matrix.
    # Note that the ordering is seemingly important for linear_sum_assignment to work.
    #  Not ordering causes points in the larger set, larger than the max size of the smaller set to be ignored.
    if len(real_coords) >= len(gen_coords):
        dist = cdist(gen_coords, real_coords)
    else:
        dist = cdist(real_coords, gen_coords)

    # Solve the assignment problem
    _, col = linear_sum_assignment(dist)

    if plot:
        # Plot generated points as blue circles, and real ones as red squares
        plt.plot(gen_coords[:, 0], gen_coords[:, 1], 'bo', markersize=10)
        plt.plot(real_coords[:, 0], real_coords[:, 1], 'rs', markersize=7)

        # Plot lines between assigned points. Note that this is also ordered.
        if len(real_coords) >= len(gen_coords):
            for p in range(0, min(len(gen_coords), len(real_coords))):
                plt.plot([gen_coords[p, 0], real_coords[col[p], 0]],
                         [gen_coords[p, 1], real_coords[col[p], 1]], 'k')
        else:
            for p in range(0, min(len(gen_coords), len(real_coords))):
                plt.plot([real_coords[p, 0], gen_coords[col[p], 0]],
                         [real_coords[p, 1], gen_coords[col[p], 1]], 'k')

        plt.show()

    # return list of assigned schools divergence
    return [dist[i, col[i]] for i in range(0, min(len(gen_coords), len(real_coords)))]


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


def test(results: list, max_distance: float):
    for result in results:
        if result >= max_distance:
            return False
    return True


def stack_test():
    """
    Taken from stack, may be useful for drawing assignment images for paper
    https://stackoverflow.com/questions/39016821/minimize-total-distance-between-two-sets-of-points-in-python
    :return:
    """
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
    # plt.axes().set_aspect('equal')  # fails


def run_tests(bound: float):
    # FIXME: Hypothesis, schools are not placed worse than 2km from real ones on average
    for test_instance in test_instances:
        divergence = calc_school_divergence(test_instance)
        total_placement_result = test(divergence, bound)
        print(f"Divergence of {test_instance.name}:")
        pprint(divergence)
        print(f"Results\n\tTotal placement:{total_placement_result}\n\tMean placement:{np.mean(divergence)}")
        # FIXME: do one sample t-test


def debug():
    divergence = calc_school_divergence(test_instances[4])
    result = test(divergence, 2000)
    print(f"Divergence of {test_instances[4].name}:")
    pprint(divergence)
    print(f"Result of test: {result}")
    print(f"Mean divergence: {np.mean(divergence)}")


if __name__ == '__main__':
    run_tests(2000)
    # debug()
