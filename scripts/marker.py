"""Explore the fluorescent marker."""

import os.path
import argparse
import warnings

import numpy as np

from jicbioimage.core.image import Image
from jicbioimage.transform import (
    max_intensity_projection,
    remove_small_objects,
)
from jicbioimage.segment import connected_components
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection, preprocess_zstack

# Suppress spurious scikit-image warnings.
warnings.filterwarnings("ignore", module="skimage.io._io")


def main():
    """Run the analysis on an indivudual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)

    zstack_proxy_iterator = microscopy_collection.zstack_proxy_iterator(c=1)
    raw, wall = preprocess_zstack(zstack_proxy_iterator, 90)

    marker = microscopy_collection.zstack_array(c=0)

    ydim, xdim, zdim = wall.shape
    for z in range(zdim):
        mask = wall[:, :, z]
        marker[:, :, z] = marker[:, :, z] * mask
        with open("marker_z{:03d}.png".format(z), "wb") as fh:
            fh.write(Image.from_array(marker[:, :, z]).png())

    max_intensity_projection(marker)

#   cutoff = np.percentile(marker[wall], 95)
    cutoff = 45
    print("cutoff: {}".format(cutoff))
    marker = marker > cutoff

    marker2D = max_intensity_projection(marker)
    marker2D = remove_small_objects(marker2D, min_size=50)

    segmentation = connected_components(marker2D, background=0)

    wall_intensity = max_intensity_projection(microscopy_collection.zstack_array(c=1))
    marker_intensity = max_intensity_projection(microscopy_collection.zstack_array(c=0))
    ann = AnnotatedImage.from_grayscale(wall_intensity,
                                        channels_on=(True, False, True))
    ann = ann + AnnotatedImage.from_grayscale(marker_intensity,
                                                 channels_on=(False, True, False))

    for i in segmentation.identifiers:
        region = segmentation.region_by_identifier(i)
        ann.mask_region(region.dilate(1).border, color=(0, 255, 255))

    with open("annotation.png", "wb") as fh:
        fh.write(ann.png())

if __name__ == "__main__":
    main()
