"""Analyse the polarity of cells using tensors."""

import os
import os.path
import argparse

import PIL
import numpy as np
import skimage.draw

from jicbioimage.core.util.array import false_color
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
    make_transparent,
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
    fpath = os.path.join(AutoName.directory, "raw_tensors.txt")
    with open(fpath, "w") as fh:
        tensors.write_raw_tensors(fh)

    # Write out intensity images.
    fpath = os.path.join(AutoName.directory, "wall_intensity.png")
    with open(fpath, "wb") as fh:
        fh.write(wall_intensity2D.png())
    fpath = os.path.join(AutoName.directory, "marker_intensity.png")
    with open(fpath, "wb") as fh:
        fh.write(marker_intensity2D.png())

    # Write out annotated images.
    colorful = false_color(cells)
    pil_im = PIL.Image.fromarray(colorful.view(dtype=np.uint8))
    pil_im = make_transparent(pil_im, 120)
    fpath = os.path.join(AutoName.directory, "segmentation.png")
    pil_im.save(fpath)

    fpath = os.path.join(AutoName.directory, "markers.png")
    with open(fpath, "wb") as fh:
        annotate_markers(markers, cells, fh)


def main():
    """Run the analysis on an individual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    parser.add_argument("output_dir", help="Output directory")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)

    microscopy_collection = get_microscopy_collection(args.input_file)
    AutoWrite.on = False
    AutoName.directory = args.output_dir
    analyse(microscopy_collection)


if __name__ == "__main__":
    main()
