"""Extract the original pixel art from an image."""

import math
import sys
from collections import Counter

import cv2
import numpy
from matplotlib import pyplot
import copy
import logging

logging.basicConfig(filename='C:/MyLog.log',level=logging.DEBUG)

def main():
    """The main entrypoint for the application."""
    image = cv2.imread('rotated_cat.png')
    #print_BGR_image(image)
    edges = cv2.Canny(image, 20, 50, L2gradient=True)
    lines = get_lines(edges)
    drawLines(lines, image)
    average_angle_offset = get_angle_offset(lines)
    average_line_distance = get_average_line_distance(lines)
    average_pixel_offset = get_average_pixel_offset(
        lines, average_line_distance)
    pixel_image, pixel_coordinates = get_pixel_image_and_coordinates(
        image, average_angle_offset, average_pixel_offset, average_line_distance)
    draw_points_on_image(image, pixel_coordinates)
    #print_BGR_image(image)
    pixel_image_crop = crop_image(pixel_image)
    mask = get_background_mask(pixel_image_crop)
    pixel_image_transparent = make_background_transparent(
        pixel_image_crop, mask)
    #print_BGRA_image(pixel_image_transparent)
    create_border(pixel_image_transparent)
    pixel_image_scaled = scale_up(pixel_image_transparent)
    print_BGRA_image(pixel_image_scaled)
    write_image_to_file(pixel_image_scaled)


def write_image_to_file(image):
    """Write an image to file."""
    filepath = "C:\\Users\\Proto\\OneDrive\\Pictures\\pixel_cat\\pixel_cat_fixed_trans_scaled_border_thicker.png"
    written = cv2.imwrite(filepath, image)
    if written:
        print("Image written to '" + filepath + "'.")
    else:
        print("Error writing file!")


def scale_up(image):
    """Scale up an image."""
    scale = 16
    height = image.shape[0]
    width = image.shape[1]
    scaled_height = height * scale
    scaled_width = width * scale
    pixel_image_scaled = numpy.full(
        (scaled_height, scaled_width, 4), [0, 0, 0, 0])
    for y in range(height):
        for x in range(width):
            for y_offset in range(y * scale, (y + 1) * scale):
                for x_offset in range(x * scale, (x + 1) * scale):
                    pixel_image_scaled[y_offset, x_offset] = image[y, x]
    return pixel_image_scaled


def create_border(image):
    """Create a border around the item in the image."""
    border_pixels = set()
    checked_pixels = set()
    find_border(image, 0, 0, border_pixels, checked_pixels)
    white_pixel = [255, 255, 255, 255]
    for border_pixel in border_pixels:
        image[border_pixel[1], border_pixel[0]] = white_pixel


def make_background_transparent(image, mask):
    """Make the background of an image transparent using a mask"""
    crop_h = image.shape[0]
    crop_w = image.shape[1]
    pixel_image_transparent = numpy.full((crop_h, crop_w, 4), [0, 0, 0, 0])
    for y in range(crop_h):
        for x in range(crop_w):
            if not mask[y+1, x+1]:
                pixel = image[y, x]
                pixel_image_transparent[y, x] = [
                    pixel[0],
                    pixel[1],
                    pixel[2],
                    255]
    return pixel_image_transparent


def get_background_mask(image):
    """Flood an image to create background mask."""
    height = image.shape[0]
    width = image.shape[1]
    mask = numpy.zeros((height+2, width+2), numpy.uint8)
    diff = 10
    diff_array = [diff, diff, diff]
    cv2.floodFill(image, mask, (0, 0), [
                  0, 0, 0], loDiff=diff_array, upDiff=diff_array)
    return mask


def crop_image(image):
    """Crop an image to 1 pixel more that image, assuming the image background is white."""
    pixel_height = image.shape[0]
    pixel_width = image.shape[1]
    top = pixel_height
    bottom = 0
    left = pixel_width
    right = 0
    for y in range(pixel_height):
        for x in range(pixel_width):
            if not numpy.array_equal(image[y, x], [255, 255, 255]):
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y
    crop_h = bottom - top + 3
    crop_w = right - left + 3
    pixel_image_crop = numpy.full((crop_h, crop_w, 3), [255, 255, 255])
    for y in range(crop_h):
        for x in range(crop_w):
            pixel_image_crop[y, x] = image[y + top - 1, x + left - 1]
    return pixel_image_crop


def get_pixel_image_and_coordinates(image, average_angle_offset, average_pixel_offset, average_line_distance):
    """Get the new image and the coordinates of the pixels in relation to the orginal image"""
    pixel_coordinates = []
    pixel_width = 200
    pixel_height = 200
    pixel_image = numpy.full((pixel_width, pixel_height, 3), [255, 255, 255])
    height = image.shape[0]
    width = image.shape[1]
    cos = numpy.cos(average_angle_offset - numpy.pi/2)
    sin = numpy.sin(average_angle_offset - numpy.pi/2)
    pixel_offset_x = (
        average_pixel_offset[0] / average_line_distance) - pixel_width/2
    pixel_offset_y = (
        average_pixel_offset[1] / average_line_distance) - pixel_height/2
    # 0.5 as we want center of 'pixel' from original image
    for pixel_y in range(pixel_height):
        for pixel_x in range(pixel_width):
            pixel_x_unit = pixel_x + 0.5 + pixel_offset_x
            pixel_y_unit = pixel_y + 0.5 + pixel_offset_y
            # get unit cords
            x_unit = (pixel_x_unit * cos) - (pixel_y_unit * sin)
            y_unit = (pixel_x_unit * sin) + (pixel_y_unit * cos)
            # scale up
            x_scaled = int(average_line_distance * x_unit)
            y_scaled = int(average_line_distance * y_unit)
            if (x_scaled < width and x_scaled >= 0 and y_scaled < height and y_scaled >= 0):
                pixel_coordinates.append((x_scaled, y_scaled))
                pixel_image[pixel_y, pixel_x] = image[y_scaled, x_scaled]
    return pixel_image, pixel_coordinates


def get_average_pixel_offset(lines, average_line_distance):
    # get the average pixel offset for x and y
    offset_sum_x = 0
    offset_sum_y = 0
    for line in lines:
        if line[1] < numpy.pi:
            offset_sum_y += line[0] % average_line_distance
        else:
            offset_sum_x += line[0] % average_line_distance
    avg_offset_x = offset_sum_x / len(lines)
    avg_offset_y = offset_sum_y / len(lines)
    return (avg_offset_x, avg_offset_y)


def get_average_line_distance(lines):
    """Get an average distance between all the lines that are 1 'pixel' apart."""
    line_distances = get_line_distances(lines)
    sorted_line_distances = Counter(line_distances).most_common()

    def filter_lambda(line_distances):
        return line_distances[0] > 5 and line_distances[0] < 20 and line_distances[1] > len(lines)/2
    valid_lengths = list(filter(filter_lambda, sorted_line_distances))
    length_sum = 0
    count = 0
    for length in valid_lengths:
        length_sum += length[0] * length[1]
        count += length[1]
    average_line_distance = length_sum / count
    return average_line_distance


def get_line_distances(lines):
    line_distances = []
    for line_1 in lines:
        for line_2 in lines:
            line_distances.append(abs(abs(line_1[0]) - abs(line_2[0])))
    return line_distances


def get_angle_offset(lines):
    """Get the average angle offset of the lines."""
    angle_sum = 0
    for line in lines:
        angle_sum += line[1] % (numpy.pi/2)
    avg_angle = angle_sum / len(lines)
    return avg_angle


def get_lines(edges):
    """Detect all lines in the image."""
    lines = cv2.HoughLines(edges, 1/2, numpy.pi/(180*2**6), 100)
    lines = lines.reshape(-1, 2).tolist()
    return lines


def print_BGR_image(image):
    """Print a BGR image."""
    temp_image = copy.deepcopy(image)
    temp_image = cv2.cvtColor(temp_image, cv2.COLOR_BGR2RGB)
    print_image(temp_image)


def print_BGRA_image(image):
    """Print a BGRA image."""
    temp_image = copy.deepcopy(image)
    b,g,r,a = cv2.split(temp_image)
    temp_image[:,:,0] = r
    temp_image[:,:,2] = b
    print_image(temp_image)


def print_image(image):
    """Print an image using pyplot."""
    pyplot.imshow(image)
    pyplot.show()


def draw_points_on_image(image, points):
    """Draw a set of points on an image."""
    for point in points:
        image[int(point[1]), int(point[0])] = [0, 0, 0]


def rotate_point(point, angle, origin=(0, 0)):
    """Rotate a point counterclockwise by a given angle in radians around a given origin."""
    o_x, o_y = origin
    p_x, p_y = point
    r_x = o_x + math.cos(angle) * (p_x - o_x) - math.sin(angle) * (p_y - o_y)
    r_y = o_y + math.sin(angle) * (p_x - o_x) + math.cos(angle) * (p_y - o_y)
    return r_x, r_y


def find_border(image, x_pos, y_pos, border_pixels, checked_pixels):
    """Recursively check neighbouring pixels to see if current pixel is a border pixel."""
    stack = [(image, x_pos, y_pos, border_pixels, checked_pixels)]
    while (len(stack)):
        arguments = stack.pop()
        image = arguments[0]
        x_pos = arguments[1]
        y_pos = arguments[2]
        border_pixels = arguments[3]
        checked_pixels = arguments[4]
        if (x_pos, y_pos) in checked_pixels:
            continue
        else:
            checked_pixels.add((x_pos, y_pos))
        height = image.shape[0]
        width = image.shape[1]
        # up
        if y_pos > 0:
            if image[y_pos - 1, x_pos][3]:
                border_pixels.add((x_pos, y_pos))
            else:
                stack.append((image, x_pos, y_pos - 1, border_pixels, checked_pixels))
                # up right
                if x_pos < width - 1:
                    if image[y_pos - 1, x_pos + 1][3]:
                        border_pixels.add((x_pos, y_pos))
                    else:
                        stack.append((image, x_pos + 1, y_pos - 1,border_pixels, checked_pixels))
        # right
        if x_pos < width - 1:
            if image[y_pos, x_pos + 1][3]:
                border_pixels.add((x_pos, y_pos))
            else:
                stack.append((image, x_pos + 1, y_pos, border_pixels, checked_pixels))
                # right down
                if y_pos < height - 1:
                    if image[y_pos + 1, x_pos + 1][3]:
                        border_pixels.add((x_pos, y_pos))
                    else:
                        stack.append((image, x_pos + 1, y_pos + 1,border_pixels, checked_pixels))
        # down
        if y_pos < height - 1:
            if image[y_pos + 1, x_pos][3]:
                border_pixels.add((x_pos, y_pos))
            else:
                stack.append((image, x_pos, y_pos+1, border_pixels, checked_pixels))
                # down left
                if x_pos > 0:
                    if (image[y_pos + 1, x_pos - 1][3]):
                        border_pixels.add((x_pos, y_pos))
                    else:
                        stack.append((image, x_pos - 1, y_pos + 1,border_pixels, checked_pixels))
        # left
        if x_pos > 0:
            if image[y_pos, x_pos - 1][3]:
                border_pixels.add((x_pos, y_pos))
            else:
                stack.append((image, x_pos - 1, y_pos, border_pixels, checked_pixels))
                if y_pos > 0:
                    if image[y_pos - 1, x_pos - 1][3]:
                        border_pixels.add((x_pos, y_pos))
                    else:
                        stack.append((image, x_pos - 1, y_pos - 1, border_pixels, checked_pixels))


def drawLines(lines, image):
    for line in lines:
        rho = line[0]
        theta = line[1]
        a = numpy.cos(theta)
        b = numpy.sin(theta)
        x0 = a*rho
        y0 = b*rho
        x1 = int(x0 + 1000*(-b))
        y1 = int(y0 + 1000*(a))
        x2 = int(x0 - 1000*(-b))
        y2 = int(y0 - 1000*(a))
        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 0), 1)


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        logging.info(e)
        

