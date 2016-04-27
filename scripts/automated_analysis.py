"""Analyse the polarity of cells using tensors."""

import os.path
import argparse

import numpy as np
import skimage.draw

from jicbioimage.core.util.color import pretty_color
from jicbioimage.core.io import (
    AutoName,
    AutoWrite,
)
from jicbioimage.illustrate import AnnotatedImage

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
)
from svg import write_svg

AutoName.prefix_format = "{:03d}_"


def analyse(microscopy_collection):
    """Do the analysis."""
    # Prepare the input data for the segmentations.
    (wall_intensity2D,
     wall_intensity3D,
     wall_mask2D,
     wall_mask3D) = get_wall_intensity_and_mask_images(microscopy_collection)
    (marker_intensity2D,
     marker_intensity3D) = get_marker_intensity_images(microscopy_collection)

    # Perform the segmentation.
    cells = cell_segmentation(wall_intensity2D, wall_mask2D)
    markers = marker_segmentation(marker_intensity3D, wall_mask3D)

    # Get tensors.
    tensors = get_tensors(cells, markers)

    # Write out tensors to a text file.
    with open("raw_tensors.txt", "w") as fh:
        tensors.write_raw_tensors(fh)

    # Write out intensity images.
    with open("wall_intensity.png", "wb") as fh:
        fh.write(wall_intensity2D.png())
    with open("marker_intensity.png", "wb") as fh:
        fh.write(marker_intensity2D.png())

    # Write out annotated images.
    with open("segmentation.png", "wb") as fh:
        annotate_segmentation(cells, fh)
    with open("markers.png", "wb") as fh:
        annotate_markers(markers, cells, fh)
    ydim, xdim = wall_mask2D.shape
    with open("tensors.png", "wb") as fh:
        annotate_tensors(ydim, xdim, tensors, fh)

    # Write out svg image.
    with open("annotated.svg", "w") as fh:
        write_svg(ydim, xdim, tensors, "segmentation.png", fh)


def main():
    """Run the analysis on an individual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)
    AutoWrite.on = False
    analyse(microscopy_collection)


if __name__ == "__main__":
    main()
