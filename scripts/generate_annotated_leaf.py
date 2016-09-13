"""Produce annotated leaf from ImageTagger tags and gaussian projections."""

import argparse
import os.path

from jicbioimage.core.io import AutoWrite, AutoName
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection
from gaussproj import (
    generate_surface_from_stack,
    projection_from_stack_and_surface,
)

def process_tag_line(line):
    image_fpath, verdict = line.split()
    name, ext = os.path.splitext(image_fpath)
    name, _ = name.rsplit("-", 1) # remove "-wall" suffix
    csv_fpath = name + ".csv"
    csv_fpath = "/".join(csv_fpath.split("/")[-5:])  # Make path relative to maek it work in docker container
    return verdict, csv_fpath

def process_csv_file(csv_fpath):
    with open(csv_fpath, "r") as fh:
        line = fh.read()
    words = line.split(",")
    centroid_row = float(words[2])
    centroid_col = float(words[3])
    marker_row = float(words[4])
    marker_col = float(words[5])
    return (centroid_row, centroid_col), (marker_row, marker_col)

def process_tags_file(tags_file):
    with open(tags_file, "r") as fh:
        for line in fh:
            verdict, csv_fpath =process_tag_line(line)
            if verdict != "good":
                continue
            centroid, marker = process_csv_file(csv_fpath)
            yield centroid, marker


def generate_annotated_leaf(microscopy_fpath, wall_channel, marker_channel, tags_fpath):
    microscopy_collection = get_microscopy_collection(microscopy_fpath)
    wall_stack = microscopy_collection.zstack_array(c=wall_channel)
    marker_stack = microscopy_collection.zstack_array(c=marker_channel)

    surface = generate_surface_from_stack(wall_stack)
    wall_projection = projection_from_stack_and_surface(wall_stack,
                                                        surface)
    marker_projection = projection_from_stack_and_surface(marker_stack,
                                                          surface)

    wall_ann = AnnotatedImage.from_grayscale(wall_projection, (1, 0, 0))
    marker_ann = AnnotatedImage.from_grayscale(marker_projection, (0, 1, 0))
    combined_ann = wall_ann + marker_ann

    for name, ann in [("wall-ann.png", wall_ann), ("marker-ann.png", marker_ann), ("combined-ann.png", combined_ann)]:
        for centroid, marker in process_tags_file(tags_fpath):
            ann.draw_line(centroid, marker, (255, 0, 255))

        fpath = os.path.join(AutoName.directory, name)
        with open(fpath, "wb") as fh:
            fh.write(ann.png())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Input microscope file.")
    parser.add_argument("tags_file", help="ImageTagger tags file.")
    parser.add_argument("output_directory", help="Output directory.")
    parser.add_argument("-w", "--wall-channel",
                        default=1, type=int,
                        help="Wall channel (zero indexed)")
    parser.add_argument("-m", "--marker-channel",
                        default=0, type=int,
                        help="Marker channel (zero indexed)")

    args = parser.parse_args()
    AutoWrite.on = False
    if not os.path.isdir(args.output_directory):
        os.mkdir(args.output_directory)
    AutoName.directory = args.output_directory

    process_tags_file(args.tags_file)
    generate_annotated_leaf(args.input_file, args.wall_channel, args.marker_channel, args.tags_file)
