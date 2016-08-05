"""Analyse the polarity of cells using tensors."""

import os
import os.path
import argparse
import logging
import warnings

import PIL
import numpy as np
import skimage.draw

from jicbioimage.core.util.array import pretty_color_array
from jicbioimage.core.io import (
    AutoName,
    AutoWrite,
)
from jicbioimage.illustrate import AnnotatedImage
from jicbioimage.transform import max_intensity_projection

from utils import (
    get_microscopy_collection,
    get_wall_intensity_and_mask_images,
    get_marker_intensity_images,
    marker_cell_identifier,
)
from segment import (
    cell_segmentation,
    marker_segmentation,
)
from tensor import get_tensors
from annotate import (
    annotate_segmentation,
    annotate_markers,
    annotate_tensors,
    make_transparent,
)

# Suppress spurious scikit-image warnings.
warnings.filterwarnings("ignore", module="skimage.morphology.misc")



AutoName.prefix_format = "{:03d}_"


def analyse(microscopy_collection, wall_channel, marker_channel, threshold, max_cell_size):
    """Do the analysis."""
    # Prepare the input data for the segmentations.
    (wall_intensity2D,
     wall_intensity3D,
     wall_mask2D,
     wall_mask3D) = get_wall_intensity_and_mask_images(microscopy_collection, wall_channel)
    (marker_intensity2D,
     marker_intensity3D) = get_marker_intensity_images(microscopy_collection, marker_channel)

    # Perform the segmentation.
    cells = cell_segmentation(wall_intensity2D, wall_mask2D, max_cell_size)
    markers = marker_segmentation(marker_intensity3D, wall_mask3D, threshold)

    # Get marker in cell wall and project to 2D.
    wall_marker = marker_intensity3D * wall_mask3D
    wall_marker = max_intensity_projection(wall_marker)

    # Get tensors.
    tensors = get_tensors(cells, markers)

    # Write out tensors to a text file.
    fpath = os.path.join(AutoName.directory, "raw_tensors.txt")
    with open(fpath, "w") as fh:
        tensors.write_raw_tensors(fh)

    # Write out intensity images.
    fpath = os.path.join(AutoName.directory, "wall_intensity.png")
    with open(fpath, "wb") as fh:
        fh.write(wall_intensity2D.png())
    fpath = os.path.join(AutoName.directory, "marker_intensity.png")
    with open(fpath, "wb") as fh:
        fh.write(wall_marker.png())

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
                        default=45, type=int,
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
