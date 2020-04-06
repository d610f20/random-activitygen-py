import random
import math
from typing import *
import collections


def _firstn(n, gen):
    for _ in range(0, n):
        yield next(gen)


def _apply(func, gen):
    """Modifies each element in generator with a given function"""
    if isinstance(gen, collections.Sequence):
        # Convert the Sequence to a Generator
        gen = iter(gen)

    for x in gen:
        yield func(x)


def _dist(point1, point2):
    return math.sqrt(
        (point1[0]-point2[0])**2.0 +
        (point1[1]-point2[1])**2.0)


def _road_point_generator(roads: List[Tuple[Tuple[float, float], Tuple[float, float]]]):
    assert len(roads) > 0

    # Compute and store the length of every road
    roads = [road for road in _apply(lambda road: (_dist(road[0], road[1]), road), roads)]

    # Length of all roads combined
    total_length = sum(_apply(lambda road_len: road_len[0], roads))

    while True:
        # Select a point on the combined stretch of road
        distance = random.uniform(0, total_length)

        # Find the selected road
        length_sum = 0.0
        found_road = False
        for road_len in roads:
            length = road_len[0]
            road = road_len[1]

            if (length_sum + length) >= distance:
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
            raise AssertionError("Failed to pick a road. A distance beyound the last road must have been erroneously picked: {} (length sum: {}) (total length: {})".format(distance, length_sum, total_length))


def _disk_generator(inner_r, outer_r, point_gen):
    # filter out points thats isn't on the disk
    def filter_disc(point, small_r, large_r):
        return small_r <= _dist((0.0, 0.0), point) <= large_r

    # points in a disk, with inner radius inner_r, and outer radius outer_r
    disk_points = filter(
            lambda point: filter_disc(point, inner_r, outer_r),
            point_gen)

    return disk_points


def _offset_disk_generator(inner_r, outer_r, offset, point_gen):
    for point in _disk_generator(inner_r, outer_r, point_gen):
        yield (point[0]+offset[0], point[1]+offset[1])


def busstop_generator(roads, inner_r, outer_r, k=10):
    """
    Bus stop placement using the poisson-disc algorithm
    """
    all_points = set()

    road_points_gen = _road_point_generator(roads)
    all_points.add(next(road_points_gen)) # Seed point

    # Yield the seed points
    for point in all_points:
        yield point

    active_points = list(all_points) # Use a list because random.choice require a sequence

    def check_dist(p, test_points, limit=inner_r):
        """
        Return true if any of the test_points is within the limit distance of P
        """
        for test_point in test_points:
            if _dist(p, test_point) < limit:
                # p is within limit distance
                return True
        # p is not within the limit distance of of the test points
        return False

    while len(active_points) > 0:
        # Pick a random point from the set of active points to be the center of the poisson disc
        center = random.choice(active_points)
        # Limit the search to K points
        gen = _firstn(k, _offset_disk_generator(inner_r, outer_r, point, road_points_gen))
        
        # Search for candidate point
        try:
            # Search for a point, or raise StopIteration is none can be found
            point = next(filter(
                    lambda p: not check_dist(p, iter(all_points)),
                    gen))

            assert not check_dist(point, all_points)

            # A new point was found
            active_points.append(point)
            all_points.add(point)

            yield point
        except StopIteration:
            # No point was found, mark center as an inactive point
            active_points.remove(center)
