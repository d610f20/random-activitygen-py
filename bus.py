import random
from utility import distance, firstn, apply


def _road_point_generator(roads):
    assert len(roads) > 0

    # Length of all roads combined
    total_length = sum(apply(lambda road: road.getLength(), roads))

    while True:
        # Select a point on the combined stretch of road
        distance = random.uniform(0, total_length)

        # Find the selected road
        length_sum = 0.0
        found_road = False
        for road in roads:
            from_node = road.getFromNode().getCoord()
            to_node = road.getToNode().getCoord()

            if (length_sum + road.getLength()) >= distance:
                # Compute the exact point on the selected road

                # Distance along the road segment
                remaining = length_sum - distance

                # Vector for the road segment
                vector = (
                        to_node[0] - from_node[0],
                        to_node[1] - from_node[1])

                # Normalized vector used for direction
                direction = (
                        vector[0]/road.getLength(),
                        vector[1]/road.getLength())

                yield [
                        from_node[0] + remaining * direction[0],
                        from_node[1] + remaining * direction[1],
                        road,
                        remaining]
                found_road = True
                break
            else:
                length_sum += road.getLength()

        if not found_road:
            raise AssertionError("Failed to pick a road. A distance beyound the last road must have been erroneously picked: {} (length sum: {}) (total length: {})".format(distance, length_sum, total_length))


def bus_stop_generator(roads, inner_r, outer_r, k=10, seeds=[]):
    """
    Bus stop placement using the poisson-disc algorithm
    """
    assert inner_r < outer_r

    all_points = set(seeds)

    road_points_gen = _road_point_generator(roads)
    if len(all_points) <= 0:
        road = tuple(next(road_points_gen))
        print(road)
        yield road
        all_points.add(road) # Seed point

    active_points = list(all_points) # Use a list because random.choice require a sequence

    def check_dist(p, test_points, limit=inner_r):
        """
        Return true if any of the test_points is within the limit distance of P
        """
        for test_point in test_points:
            if distance((p[0], p[1]), (test_point[0], test_point[1])) < limit:
                # p is within limit distance
                return True
        # p is not within the limit distance of of the test points
        return False

    while len(active_points) > 0:
        # Pick a random point from the set of active points to be the center of the poisson disc
        center = random.choice(active_points)
        # Limit the search to K points
        gen = firstn(k, filter(
                lambda point: inner_r <= distance((center[0], center[1]), (point[0], point[1])) <= outer_r,
                road_points_gen))

        # Search for candidate point
        try:
            # Search for a point, or raise StopIteration is none can be found
            point = next(filter(
                    lambda p: not check_dist(p, iter(all_points)),
                    gen))

            assert not check_dist(point, all_points)

            # A new point was found
            active_points.append(point)
            all_points.add(tuple(point))

            print(point)

            yield point
        except StopIteration:
            # No point was found, mark center as an inactive point
            active_points.remove(center)
