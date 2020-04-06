import random
import math
from typing import *
import collections


def firstn(n, gen):
    for _ in range(0, n):
        yield next(gen)


def apply(func, gen):
    """Modifies each element in generator with a given function"""
    if isinstance(gen, collections.Sequence):
        # Convert the Sequence to a Generator
        gen = iter(gen)

    for x in gen:
        yield func(x)


def dist(point1, point2):
    return math.sqrt(
        (point1[0]-point2[0])**2.0 +
        (point1[1]-point2[1])**2.0)


def road_point_generator(roads: List[Tuple[Tuple[float, float], Tuple[float, float]]]):
    assert len(roads) > 0

    # Compute and store the length of every road
    roads = [road for road in apply(lambda road: (dist(road[0], road[1]), road), roads)]

    # Length of all roads combined
    total_length = sum(apply(lambda road_len: road_len[0], roads))

    while True:
        # Select a point on the combined stretch of road
        distance = random.uniform(0, total_length)
        # Find the selected road
        length_sum = 0.0
        found_road = False
        for road_len in roads:
            length = road_len[0]
            road = road_len[1]

            if length_sum >= distance:
                # Compute the exact point on the selected road

                # Distance along the road segment
                remaining = length_sum - distance

                # Vector for the road segment
                vector = (
                        road[1][0] - road[0][0],
                        road[1][1] - road[0][1])

                # Normalized vector used for direction
                direction = (
                        vector[0]/length,
                        vector[1]/length)

                yield (
                        road[0][0] + remaining * direction[0],
                        road[0][1] + remaining * direction[1],
                        road,
                        remaining)
                found_road = True
                break
            else:
                length_sum += length

        if not found_road:
            raise AssertionError("Failed to pick a road. A distance beyound the last road must have been erroneously picked: {} (total: {})".format(length_sum, total_length))


example_roads = [
        (( 0.0,  0.0), ( 0.0,  2.0)),
        (( 0.0,  0.0), ( 2.0,  2.0)),
        (( 0.0,  0.0), ( 2.0,  0.0)),
        (( 0.0,  0.0), ( 2.0, -2.0)),
        (( 0.0,  0.0), ( 0.0, -2.0)),
        (( 0.0,  0.0), (-2.0, -2.0)),
        (( 0.0,  0.0), (-2.0,  0.0)),
        (( 0.0,  0.0), (-2.0,  2.0)),
        (( 0.0,  2.0), ( 2.0,  0.0)),
        (( 2.0,  0.0), ( 0.0, -2.0)),
        (( 0.0, -2.0), (-2.0,  0.0)),
        ((-2.0,  0.0), ( 0.0,  2.0)),
        (( 2.0,  0.0), ( 2.0,  2.0)),
        (( 2.0,  2.0), ( 2.0,  0.0)),
        (( 2.0,  0.0), ( 2.0, -2.0)),
        (( 2.0, -2.0), ( 0.0, -2.0)),
        (( 0.0, -2.0), (-2.0, -2.0)),
        ((-2.0, -2.0), (-2.0,  0.0)),
        ((-2.0,  0.0), (-2.0, -2.0)),
        ((-2.0, -2.0), ( 0.0,  2.0))
        ]


def disk_generator(inner_r, outer_r):
    # random number with in a the outer circle of the disk (only in 1D)
    #random_interval = lambda: random.uniform(-outer_r, outer_r)

    # points in a square
    #square_points = zip(
    #    iter(random_interval, 1), 
    #    iter(random_interval, 1))

    square_points = road_point_generator(roads)

    # filter out points thats isn't on the disk
    def filter_disc(point, small_r, large_r):
        return small_r <= dist((0.0, 0.0), point) <= large_r

    # points in a disk, with inner radius inner_r, and outer radius outer_r
    disk_points = filter(
            lambda point: filter_disc(point, inner_r, outer_r),
            square_points)

    return disk_points


def offset_disk_generator(inner_r, outer_r, offset):
    disk_points = disk_generator(inner_r, outer_r)

    while True:
        point = next(disk_points)
        yield (point[0]+offset[0], point[1]+offset[1])


def poision_disk_generator(inner_r, outer_r, seeds, bounds, k=10):
    # make sure the lower left point is first
    assert len(bounds) >= 4

    if bounds[0] > bounds[2]:
        bounds[0], bounds[2] = bounds[2], bounds[0]

    if bounds[1] > bounds[3]:
        bounds[1], bounds[3] = bounds[3], bounds[1]

    in_bounds = lambda p: bounds[0] < p[0] and p[0] < bounds[2] and bounds[1] < p[1] and p[1] < bounds[3]

    active_points = list(set(seeds)) # Remove duplicates, but use a list because random.choice require a sequence
    all_points = set(seeds)

    for point in all_points:
        yield point

    def check_dist(p, test_points, limit=inner_r):
        """
        Return true if any of the test_points within the limit distance of any of the test points
        """
        for test_point in test_points:
            if dist(p, test_point) < limit:
                # p is with in limit distance
                return True
        # p is not with in the limit distance of of the test points
        return False

    while len(active_points) > 0:
        center = random.choice(active_points)
        gen = firstn(k, offset_disk_generator(inner_r, outer_r, point))
        
        # Search for candidate point
        try:
            bounded_gen = filter(
                    in_bounds,
                    gen)
            point = next(filter(
                    lambda p: not check_dist(p, iter(all_points)),
                    bounded_gen))

            assert not check_dist(point, all_points)
            assert in_bounds(point)

            # A new point was found
            active_points.append(point)
            all_points.add(point)

            yield point
        except StopIteration:
            # No point was found, mark center as an inactive point
            active_points.remove(center)
