import os
import sys
from typing import Tuple

import noise
import numpy as np
import math
import xml.etree.ElementTree as ET
from PIL import Image, ImageOps, ImageChops, ImageDraw

from perlin import get_perlin_noise, POPULATION_BASE, INDUSTRY_BASE, get_edge_pair_centroid
from utility import find_city_centre, radius_of_network, distance

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME' to use sumolib")

import sumolib


def display_network(net: sumolib.net.Net, stats: ET.ElementTree, max_width: int, max_height: int, centre: Tuple[float, float], perlin_scale: float = 0.005, octave: int = 3):
    """
    :param net: the network to display noisemap for
    :param stats: the stats file describing the network
    :param perlin_scale: the scale to multiply to each coordinate, default is 0.005
    :param octave: the octaves to use when sampling, default is 3
    :return:
    """
    # Basics about the city and its size
    boundary = net.getBoundary()
    city_size = (boundary[2], boundary[3])
    city_radius = radius_of_network(net, centre)

    # Determine the size of the picture and scalars for scaling the city to the correct size
    # We might have a very wide city. In this case we want to produce a wide image
    width_height_relation = city_size[1] / city_size[0]
    width, height = (max_width, int(max_height * width_height_relation)) if city_size[0] > city_size[1] else (int(max_width / width_height_relation), max_height)
    width_scale = width / city_size[0]
    height_scale = height / city_size[1]

    # Make image and prepare for drawing
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Draw streets
    for street_xml in stats.find("streets").findall("street"):
        edge = net.getEdge(street_xml.attrib["edge"])
        population = float(street_xml.attrib["population"])
        industry = float(street_xml.attrib["workPosition"])
        x1, y1 = edge.getFromNode().getCoord()
        x2, y2 = edge.getToNode().getCoord()
        green = int(min(max(0, population * 190 - 30), 255))
        blue = int(min(max(0, industry * 255 - 20), 255))
        draw.line([x1 * width_scale, y1 * height_scale, x2 * width_scale, y2 * height_scale], (0, green, blue), int(0.5 + population * 4))

    # Draw city gates
    for gate_xml in stats.find("cityGates").findall("entrance"):
        edge = net.getEdge(gate_xml.attrib["edge"])
        traffic = max(float(gate_xml.attrib["incoming"]), float(gate_xml.attrib["outgoing"]))
        x, y = get_edge_pair_centroid(edge.getShape())
        x *= width_scale
        y *= height_scale
        r = int(2 + traffic / 1.3)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 0, 0))

    # Draw schools
    for school_xml in stats.find("schools").findall("school"):
        edge = net.getEdge(school_xml.attrib["edge"])
        capacity = int(school_xml.get('capacity'))
        x, y = get_edge_pair_centroid(edge.getShape())
        x *= width_scale
        y *= height_scale
        r = int(2 + capacity / 175)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 216, 0))

    img.show()


_errstr = "Mode is unknown or incompatible with input array shape."


def bytescale(data, cmin=None, cmax=None, high=255, low=0):
    """
    Byte scales an array (image).
    Byte scaling means converting the input image to uint8 dtype and scaling
    the range to ``(low, high)`` (default 0-255).
    If the input image already has dtype uint8, no scaling is done.
    This function is only available if Python Imaging Library (PIL) is installed.
    Parameters
    ----------
    data : ndarray
        PIL image data array.
    cmin : scalar, optional
        Bias scaling of small values. Default is ``data.min()``.
    cmax : scalar, optional
        Bias scaling of large values. Default is ``data.max()``.
    high : scalar, optional
        Scale max value to `high`.  Default is 255.
    low : scalar, optional
        Scale min value to `low`.  Default is 0.
    Returns
    -------
    img_array : uint8 ndarray
        The byte-scaled array.
    Examples
    --------
    >>> from scipy.misc import bytescale
    >>> img = np.array([[ 91.06794177,   3.39058326,  84.4221549 ],
    ...                 [ 73.88003259,  80.91433048,   4.88878881],
    ...                 [ 51.53875334,  34.45808177,  27.5873488 ]])
    >>> bytescale(img)
    array([[255,   0, 236],
           [205, 225,   4],
           [140,  90,  70]], dtype=uint8)
    >>> bytescale(img, high=200, low=100)
    array([[200, 100, 192],
           [180, 188, 102],
           [155, 135, 128]], dtype=uint8)
    >>> bytescale(img, cmin=0, cmax=255)
    array([[91,  3, 84],
           [74, 81,  5],
           [52, 34, 28]], dtype=uint8)
    """
    if data.dtype == np.uint8:
        return data

    if high > 255:
        raise ValueError("`high` should be less than or equal to 255.")
    if low < 0:
        raise ValueError("`low` should be greater than or equal to 0.")
    if high < low:
        raise ValueError("`high` should be greater than or equal to `low`.")

    if cmin is None:
        cmin = data.min()
    if cmax is None:
        cmax = data.max()

    cscale = cmax - cmin
    if cscale < 0:
        raise ValueError("`cmax` should be larger than `cmin`.")
    elif cscale == 0:
        cscale = 1

    scale = float(high - low) / cscale
    bytedata = (data - cmin) * scale + low
    return (bytedata.clip(low, high) + 0.5).astype(np.uint8)


def toimage(arr, high=255, low=0, cmin=None, cmax=None, pal=None,
            mode=None, channel_axis=None):
    """Takes a numpy array and returns a PIL image.
    This function is only available if Python Imaging Library (PIL) is installed.
    The mode of the PIL image depends on the array shape and the `pal` and
    `mode` keywords.
    For 2-D arrays, if `pal` is a valid (N,3) byte-array giving the RGB values
    (from 0 to 255) then ``mode='P'``, otherwise ``mode='L'``, unless mode
    is given as 'F' or 'I' in which case a float and/or integer array is made.
    .. warning::
        This function uses `bytescale` under the hood to rescale images to use
        the full (0, 255) range if ``mode`` is one of ``None, 'L', 'P', 'l'``.
        It will also cast data for 2-D images to ``uint32`` for ``mode=None``
        (which is the default).
    Notes
    -----
    For 3-D arrays, the `channel_axis` argument tells which dimension of the
    array holds the channel data.
    For 3-D arrays if one of the dimensions is 3, the mode is 'RGB'
    by default or 'YCbCr' if selected.
    The numpy array must be either 2 dimensional or 3 dimensional.
    """
    data = np.asarray(arr)
    if np.iscomplexobj(data):
        raise ValueError("Cannot convert a complex-valued array.")
    shape = list(data.shape)
    valid = len(shape) == 2 or ((len(shape) == 3) and
                                ((3 in shape) or (4 in shape)))
    if not valid:
        raise ValueError("'arr' does not have a suitable array shape for "
                         "any mode.")
    if len(shape) == 2:
        shape = (shape[1], shape[0])  # columns show up first
        if mode == 'F':
            data32 = data.astype(np.float32)
            image = Image.frombytes(mode, shape, data32.tostring())
            return image
        if mode in [None, 'L', 'P']:
            bytedata = bytescale(data, high=high, low=low,
                                 cmin=cmin, cmax=cmax)
            image = Image.frombytes('L', shape, bytedata.tostring())
            if pal is not None:
                image.putpalette(np.asarray(pal, dtype=np.uint8).tostring())
                # Becomes a mode='P' automagically.
            elif mode == 'P':  # default gray-scale
                pal = (np.arange(0, 256, 1, dtype=np.uint8)[:, np.newaxis] *
                       np.ones((3,), dtype=np.uint8)[np.newaxis, :])
                image.putpalette(np.asarray(pal, dtype=np.uint8).tostring())
            return image
        if mode == '1':  # high input gives threshold for 1
            bytedata = (data > high)
            image = Image.frombytes('1', shape, bytedata.tostring())
            return image
        if cmin is None:
            cmin = np.amin(np.ravel(data))
        if cmax is None:
            cmax = np.amax(np.ravel(data))
        data = (data * 1.0 - cmin) * (high - low) / (cmax - cmin) + low
        if mode == 'I':
            data32 = data.astype(np.uint32)
            image = Image.frombytes(mode, shape, data32.tostring())
        else:
            raise ValueError(_errstr)
        return image

    # if here then 3-d array with a 3 or a 4 in the shape length.
    # Check for 3 in datacube shape --- 'RGB' or 'YCbCr'
    if channel_axis is None:
        if (3 in shape):
            ca = np.flatnonzero(np.asarray(shape) == 3)[0]
        else:
            ca = np.flatnonzero(np.asarray(shape) == 4)
            if len(ca):
                ca = ca[0]
            else:
                raise ValueError("Could not find channel dimension.")
    else:
        ca = channel_axis

    numch = shape[ca]
    if numch not in [3, 4]:
        raise ValueError("Channel axis dimension is not valid.")

    bytedata = bytescale(data, high=high, low=low, cmin=cmin, cmax=cmax)
    if ca == 2:
        strdata = bytedata.tostring()
        shape = (shape[1], shape[0])
    elif ca == 1:
        strdata = np.transpose(bytedata, (0, 2, 1)).tostring()
        shape = (shape[2], shape[0])
    elif ca == 0:
        strdata = np.transpose(bytedata, (1, 2, 0)).tostring()
        shape = (shape[2], shape[1])
    if mode is None:
        if numch == 3:
            mode = 'RGB'
        else:
            mode = 'RGBA'

    if mode not in ['RGB', 'RGBA', 'YCbCr', 'CMYK']:
        raise ValueError(_errstr)

    if mode in ['RGB', 'YCbCr']:
        if numch != 3:
            raise ValueError("Invalid array shape for mode.")
    if mode in ['RGBA', 'CMYK']:
        if numch != 4:
            raise ValueError("Invalid array shape for mode.")

    # Here we know data and mode is correct
    image = Image.frombytes(mode, shape, strdata)
    return image


def example():
    shape = (1024, 1024)
    scale = 100
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0
    seed = np.random.randint(0, 100)

    world = np.zeros(shape)
    for i in range(shape[0]):
        for j in range(shape[1]):
            world[i][j] = noise.pnoise2(i / scale,
                                        j / scale,
                                        octaves=octaves,
                                        persistence=persistence,
                                        lacunarity=lacunarity,
                                        repeatx=1024,
                                        repeaty=1024,
                                        base=seed)

    blue = [65, 105, 225]
    green = [34, 139, 34]
    beach = [238, 214, 175]
    snow = [255, 250, 250]
    mountain = [139, 137, 137]

    def add_color(world):
        color_world = np.zeros(world.shape + (3,))
        for i in range(shape[0]):
            for j in range(shape[1]):
                if world[i][j] < -0.05:
                    color_world[i][j] = blue
                elif world[i][j] < 0:
                    color_world[i][j] = beach
                elif world[i][j] < .20:
                    color_world[i][j] = green
                elif world[i][j] < 0.35:
                    color_world[i][j] = mountain
                elif world[i][j] < 1.0:
                    color_world[i][j] = snow

        return color_world

    color_world = add_color(world)

    a, b = shape[0] / 2, shape[1] / 2
    n = 1024
    r = 125
    y, x = np.ogrid[-a:n - a, -b:n - b]
    # creates a mask with True False values
    # at indices
    mask = x ** 2 + y ** 2 <= r ** 2

    black = [0, 0, 0]
    island_world = np.zeros_like(color_world)

    for i in range(shape[0]):
        for j in range(shape[1]):
            if mask[i][j]:
                island_world[i][j] = color_world[i][j]
            else:
                island_world[i][j] = black

    center_x, center_y = shape[1] // 2, shape[0] // 2
    circle_grad = np.zeros_like(world)

    for y in range(world.shape[0]):
        for x in range(world.shape[1]):
            distx = abs(x - center_x)
            disty = abs(y - center_y)
            dist = math.sqrt(distx * distx + disty * disty)
            circle_grad[y][x] = dist

    # get it between -1 and 1
    max_grad = np.max(circle_grad)
    circle_grad = circle_grad / max_grad
    circle_grad -= 0.5
    circle_grad *= 2.0
    circle_grad = -circle_grad

    # shrink gradient
    for y in range(world.shape[0]):
        for x in range(world.shape[1]):
            if circle_grad[y][x] > 0:
                circle_grad[y][x] *= 20

    # get it between 0 and 1
    max_grad = np.max(circle_grad)
    circle_grad = circle_grad / max_grad

    # toimage(island_world).show()

    world_noise = np.zeros_like(world)

    for i in range(shape[0]):
        for j in range(shape[1]):
            world_noise[i][j] = (world[i][j] * circle_grad[i][j])
            if world_noise[i][j] > 0:
                world_noise[i][j] *= 20

    # get it between 0 and 1
    max_grad = np.max(world_noise)
    world_noise = world_noise / max_grad

    # toimage(world_noise).show()

    lightblue = [0, 191, 255]
    blue = [65, 105, 225]
    green = [34, 139, 34]
    darkgreen = [0, 100, 0]
    sandy = [210, 180, 140]
    beach = [238, 214, 175]
    snow = [255, 250, 250]
    mountain = [139, 137, 137]

    threshold = 0.2

    def add_color2(world):
        color_world = np.zeros(world.shape + (3,))
        for i in range(shape[0]):
            for j in range(shape[1]):
                if world[i][j] < threshold + 0.05:
                    color_world[i][j] = blue
                elif world[i][j] < threshold + 0.055:
                    color_world[i][j] = sandy
                elif world[i][j] < threshold + 0.1:
                    color_world[i][j] = beach
                elif world[i][j] < threshold + 0.25:
                    color_world[i][j] = green
                elif world[i][j] < threshold + 0.6:
                    color_world[i][j] = darkgreen
                elif world[i][j] < threshold + 0.7:
                    color_world[i][j] = mountain
                elif world[i][j] < threshold + 1.0:
                    color_world[i][j] = snow

        return color_world

    island_world_grad = add_color2(world_noise)
    toimage(island_world_grad).show()


def trash():
    shape = (1024, 1024)
    scale = 100
    octaves = 6
    persistence = 0.5
    lacunarity = 2.0
    seed = 0

    world = np.zeros(shape)
    for i in range(shape[0]):
        for j in range(shape[1]):
            world[i][j] = noise.pnoise2(i / scale,
                                        j / scale,
                                        octaves=octaves,
                                        persistence=persistence,
                                        lacunarity=lacunarity,
                                        repeatx=1024,
                                        repeaty=1024,
                                        base=seed)

    x_axis = np.linspace(-1, 1, 1024)[:, None]
    y_axis = np.linspace(-1, 1, 1024)[None, :]
    arr = np.sqrt(x_axis ** 2 + y_axis ** 2)

    print(f"edge value: {arr[0][0]} center value: {arr[512][512]}")

    toimage(arr).show()

    for i in range(shape[0]):
        for j in range(shape[1]):
            world[i][j] = world[i][j] + (1 - arr[i][j])

    toimage(world).show()
