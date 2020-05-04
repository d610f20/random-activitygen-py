import os
import subprocess
import sys
from pathlib import Path
from pprint import pprint
import random
from sys import stderr

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
import xml.etree.ElementTree as ET

from scipy.stats import ttest_1samp

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
    TestInstance("Esbjerg", "in/cities/esbjerg.net.xml", "in/cities/esbjerg.stat.xml", "out/cities/esbjerg.stat.xml",
                 "stats/esbjerg.stat.xml"),
    TestInstance("Slagelse", "in/cities/slagelse.net.xml", "in/cities/slagelse.stat.xml",
                 "out/cities/slagelse.stat.xml", "stats/slagelse.stat.xml"),
    TestInstance("Randers", "in/cities/randers.net.xml", "in/cities/randers.stat.xml", "out/cities/randers.stat.xml",
                 "stats/randers.stat.xml"),
    TestInstance("Vejen", "in/cities/vejen.net.xml", "in/cities/vejen.stat.xml", "out/cities/vejen.stat.xml",
                 "stats/vejen.stat.xml"),
    TestInstance("Aalborg", "in/cities/aalborg.net.xml", "in/cities/aalborg.stat.xml", "out/cities/aalborg.stat.xml",
                 "stats/aalborg.stat.xml")
]


def calc_school_divergence(test: TestInstance, plot: bool):
    """
    Calculate the divergence between generated and real schools by solving the assignment problem on them
     and plot these schools and assignments on the network if enabled.
    :param test: the given TestInstance to test
    :param plot: whether to plot the city, schools, and assignments
    :return: the divergence for each assigned school
    """
    net: sumolib.net.Net = sumolib.net.readNet(test.net_file)

    # Get mean school coordinates for real and generated statistics
    gen_coords = np.array(get_mean_coords([net.getEdge(xml_school.get("edge")).getShape() for xml_school in
                                           ET.parse(test.gen_stats_out_file).find("schools").findall("school")]))
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
    _, assignment = linear_sum_assignment(dist)

    if plot:
        plot_school_assignment(net, test.name, gen_coords, real_coords, assignment)

    # return list of assigned schools divergence
    return [dist[i, assignment[i]] for i in range(0, min(len(gen_coords), len(real_coords)))]


def plot_school_assignment(net: sumolib.net.Net, test_name: str, gen_coords: np.ndarray, real_coords: np.ndarray,
                           assignment: np.ndarray):
    # Draw streets
    [plt.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], "grey") for pos1, pos2 in
     [edge.getShape()[i:i + 2] for edge in net.getEdges() for i in range(0, int(len(edge.getShape()) - 1))]]

    # Plot generated points as blue circles, and real ones as red squares
    plt.plot(gen_coords[:, 0], gen_coords[:, 1], 'bo', markersize=10, label="Gen")
    plt.plot(real_coords[:, 0], real_coords[:, 1], 'rs', markersize=7, label="Real")

    # Plot lines between assigned points. Note that this is also ordered, hence the swap
    if len(real_coords) <= len(gen_coords):
        real_coords, gen_coords = gen_coords, real_coords
    for p in range(0, min(len(gen_coords), len(real_coords))):
        plt.plot([gen_coords[p, 0], real_coords[assignment[p], 0]],
                 [gen_coords[p, 1], real_coords[assignment[p], 1]], 'k', label="Assign" if p == 0 else "")

    plt.legend()
    plt.title(f"School placement test for {test_name}")
    plt.show()


def get_mean_coords(schools: list):
    """
    Takes a list of schools and returns a list of schools with their coordinates averaged out
    :param schools: the list of schools to get mean coords of
    :return: a new list of the schools mean coordinates
    """
    # Get centre of each school edge coordinate
    normalised_coords = []
    for school in schools:
        x, y = [], []
        for coords in school:
            x.append(coords[0])
            y.append(coords[1])
        normalised_coords.append((np.mean(x), np.mean(y)))
    return normalised_coords


def test_total_placement(results: list, max_distance: float):
    """
    Tests whether each result is within some max distance
    :param results: a list of results/divergences
    :param max_distance: the max distance to test for
    :return: bool whether all are placed within max distance
    """
    for result in results:
        if result >= max_distance:
            return False
    return True


def t_test(test: TestInstance, divs: list, bound: float, times: int):
    print(f"Executing school placement one-sided t-test on {times} runs of {test.name}")
    # Flatten list of divergences
    divs = [dist for div in divs for dist in div]

    print(f"\tAll schools placed closer than bound: {test_total_placement(divs, bound)}")
    print(f"\tMean divergence: {np.mean(divs):.2f} meters")
    if len(divs) < 2:
        print("\t[WARN] Cannot make a t-test on a single divergence")
        if np.mean(divs) <= bound:
            print(f"\tHowever, the divergence ({np.mean(divs):.2f} meters) is less or equal than {bound}")
        else:
            print(f"\tHowever, the divergence ({np.mean(divs):.2f} meters) is greater than {bound}", )
        return
    t_stat, p_val = ttest_1samp(divs, bound)
    # To obtain a one-sided p-value, divide by 2 as the probability density function is symmetric
    p_val = p_val / 2

    print(f"\tT-test with bound {bound} meters. T-stat: {t_stat:.5f}, p-value: {p_val:.5f}")
    if t_stat <= 0:
        if p_val <= 0.05:
            print(f"\tSince t-stat is zero or negative, and p-value is of statistical significance (p <= 0.05), "
                  f"the null-hypothesis can be rejected.")
        else:
            print("\tSince p-value is not of statistical significance, the null-hypothesis cannot be rejected.")
    else:
        if p_val <= 0.05:
            print("\tThe t-stat is not zero or negative, and p-value is of statistical significance (p <= 0.05),"
                  "the null-hypothesis cannot be rejected.")
        else:
            print("\tSince p-value is not of statistical significance, the null-hypothesis cannot be rejected.")


def run_multiple_test(test: TestInstance, bound: float, times: int):
    # execute a test-instance n times
    divs = []
    for n in range(0, times):
        # run main
        subprocess.run(
            ["python", "./randomActivityGen.py", f"--net-file={test.net_file}", f"--stat-file={test.gen_stats_in_file}",
             f"--output-file={test.gen_stats_out_file}", "--quiet", f"--random"])
        # calculate and collect derivations
        divs += [calc_school_divergence(test, False)]
    # test within bound on derivations
    t_test(test, divs, bound, times)


if __name__ == '__main__':
    bound = 1150
    print(f"Testing school placement on following cities: {', '.join([test.name for test in test_instances])}")
    print(f"Null hypothesis: Generated schools are placed further than {bound} meters away from real schools")
    print(f"Alt. hypothesis: Generated schools are placed exactly or closer than {bound} meters away from real schools")
    # [t_test(test, calc_school_divergence(test, True), bound, 1) for test in test_instances]  # One run per test
    [run_multiple_test(test, 1150, 10) for test in test_instances]  # Multiple runs per test
