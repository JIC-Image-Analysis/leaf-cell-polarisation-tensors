"""Save out .png images of individual cells."""
import os
import os.path
import argparse
import logging

import numpy as np

from jicbioimage.core.image import Image
from jicbioimage.core.io import AutoName, AutoWrite

from utils import get_microscopy_collection

from gaussproj import (
    generate_surface_from_stack,
    projection_from_stack_and_surface,
)

from automated_gaussproj_analysis import segment_cells


def write_cells(cells, cell_wall_projection):
    """Write out png images of individual cells."""
    masked = np.copy(cell_wall_projection).view(Image)
    for i in cells.identifiers:
        np.copyto(masked, cell_wall_projection)
        fpath = os.path.join(AutoName.directory, "{:04d}.png".format(i))

        region = cells.region_by_identifier(i)
        masked[np.logical_not(region)] = 0
        yis, xis = region.index_arrays

        with open(fpath, "wb") as fh:
            fh.write(masked[np.min(yis):np.max(yis),
                            np.min(xis):np.max(xis)].png())


def analyse(microscopy_collection, wall_channel, marker_channel,
            threshold, max_cell_size):
    """Do the analysis."""
    # Prepare the input data for the segmentations.
    cell_wall_stack = microscopy_collection.zstack_array(c=wall_channel)
    surface = generate_surface_from_stack(cell_wall_stack)
    cell_wall_projection = projection_from_stack_and_surface(cell_wall_stack,
                                                             surface, 1, 9)

    # Perform the segmentation.
    cells, wall = segment_cells(cell_wall_projection, max_cell_size)
    write_cells(cells, cell_wall_projection)


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
