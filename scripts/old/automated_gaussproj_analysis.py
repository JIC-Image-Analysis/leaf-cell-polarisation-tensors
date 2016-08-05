"""Analyse the polarity of cells using tensors.

This script makes use of a Gaussian projection as a pre-processing step prior
to segmentation of the cell wall and marker channels.
"""

import os
import os.path
import argparse
import logging

import PIL
import numpy as np
import skimage.feature

from jicbioimage.core.util.array import pretty_color_array
from jicbioimage.core.transform import transformation
from jicbioimage.core.io import (
    AutoName,
    AutoWrite,
)
from jicbioimage.transform import (
    invert,
    dilate_binary,
    remove_small_objects,
)
from jicbioimage.segment import connected_components, watershed_with_seeds


from utils import (
    get_microscopy_collection,
    threshold_abs,
    identity,
    remove_large_segments,
)
from tensor import get_tensors
from annotate import make_transparent
from gaussproj import (
    generate_surface_from_stack,
    projection_from_stack_and_surface,
)

AutoName.prefix_format = "{:03d}_"


@transformation
def threshold_adaptive_median(image, block_size):
    return skimage.filters.threshold_adaptive(image, block_size=block_size)


@transformation
def marker_in_wall(marker, wall):
    return marker * wall


def segment_cells(image, max_cell_size):
    """Return segmented cells."""
    image = identity(image)

    wall = threshold_adaptive_median(image, block_size=101)
    seeds = remove_small_objects(wall, min_size=100)
    seeds = dilate_binary(seeds)
    seeds = invert(seeds)
    seeds = remove_small_objects(seeds, min_size=5)
    seeds = connected_components(seeds, background=0)

    segmentation = watershed_with_seeds(-image, seeds=seeds)
    segmentation = remove_large_segments(segmentation, max_cell_size)
    return segmentation, wall


def segment_markers(image, wall, threshold):
    """Return segmented markers."""
    image = threshold_abs(image, threshold)
    image = marker_in_wall(image, wall)
    image = remove_small_objects(image, min_size=10)

    segmentation = connected_components(image, background=0)
    return segmentation


def analyse(microscopy_collection, wall_channel, marker_channel,
            threshold, max_cell_size):
    """Do the analysis."""
    # Prepare the input data for the segmentations.
    cell_wall_stack = microscopy_collection.zstack_array(c=wall_channel)
    marker_stack = microscopy_collection.zstack_array(c=marker_channel)
    surface = generate_surface_from_stack(cell_wall_stack)
    cell_wall_projection = projection_from_stack_and_surface(cell_wall_stack,
                                                             surface, 1, 9)
    marker_projection = projection_from_stack_and_surface(marker_stack,
                                                          surface, 1, 9)

    # Perform the segmentation.
    cells, wall = segment_cells(cell_wall_projection, max_cell_size)
    markers = segment_markers(marker_projection, wall, threshold)

    # Get tensors.
    tensors = get_tensors(cells, markers)

    # Write out tensors to a text file.
    fpath = os.path.join(AutoName.directory, "raw_tensors.txt")
    with open(fpath, "w") as fh:
        tensors.write_raw_tensors(fh)

    # Write out intensity images.
    fpath = os.path.join(AutoName.directory, "wall_intensity.png")
    with open(fpath, "wb") as fh:
        fh.write(cell_wall_projection.png())
    fpath = os.path.join(AutoName.directory, "marker_intensity.png")
    marker_im = marker_in_wall(marker_projection, wall)
    with open(fpath, "wb") as fh:
        fh.write(marker_im.png())

    # Shrink the segments to make them clearer.
    for i in cells.identifiers:
        region = cells.region_by_identifier(i)
        mask = region - region.inner.inner
        cells[mask] = 0
    colorful = pretty_color_array(cells)
    pil_im = PIL.Image.fromarray(colorful.view(dtype=np.uint8))
    pil_im = make_transparent(pil_im, 60)
    fpath = os.path.join(AutoName.directory, "segmentation.png")
    pil_im.save(fpath)


def main():
    """Run the analysis on an individual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("-w", "--wall-channel",
                        default=1, type=int,
                        help="Wall channel (zero indexed)")
    parser.add_argument("-m", "--marker-channel",
                        default=0, type=int,
                        help="Marker channel (zero indexed)")
    parser.add_argument("-t", "--threshold",
                        default=60, type=int,
                        help="Marker threshold")
    parser.add_argument("-s", "--max-cell-size",
                        default=10000, type=int,
                        help="Maximum cell size (pixels)")
    parser.add_argument("--debug",
                        default=False, action="store_true")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    AutoName.directory = args.output_dir
    AutoWrite.on = args.debug
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    logging.info("Input file: {}".format(args.input_file))
    logging.info("Wall channel: {}".format(args.wall_channel))
    logging.info("Marker channel: {}".format(args.marker_channel))
    logging.info("Marker threshold: {}".format(args.threshold))
    logging.info("Max cell size: {}".format(args.max_cell_size))

    microscopy_collection = get_microscopy_collection(args.input_file)
    analyse(microscopy_collection,
            wall_channel=args.wall_channel,
            marker_channel=args.marker_channel,
            threshold=args.threshold,
            max_cell_size=args.max_cell_size)


if __name__ == "__main__":
    main()
