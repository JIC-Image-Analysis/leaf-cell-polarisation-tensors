"""Segment leaf into individual cells."""

import os.path
import argparse
import warnings

import numpy as np

from jicbioimage.core.transform import transformation
from jicbioimage.core.util.color import pretty_color
from jicbioimage.core.io import AutoWrite
from jicbioimage.transform import (
    max_intensity_projection,
    remove_small_objects,
    invert,
    dilate_binary,
)
from jicbioimage.segment import connected_components, watershed_with_seeds
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection

# Suppress spurious scikit-image warnings.
warnings.filterwarnings("ignore", module="skimage.io._io")




@transformation
def threshold_mean(image):
    """Return image thresholded using the mean."""
    return image > np.mean(image)


@transformation
def threshold_percentile(image, percentile):
    """Return image thresholded using the mean."""
    return image > np.percentile(image, percentile)


@transformation
def threshold_abs(image, threshold):
    """Return image thresholded using the mean."""
    return image > threshold


@transformation
def identity(image):
    return image


def segment_zslice(image):
    """Segment a zslice."""
    tmp_autowrite = AutoWrite.on
    AutoWrite.on = False
    image = identity(image)
    image = threshold_abs(image, 100)
    image = remove_small_objects(image, min_size=500)
    AutoWrite.on = tmp_autowrite
    return image


def preprocess_zstack(zstack_proxy_iterator, cutoff):
    """Select the pixels where the signal is."""
    raw = []
    zstack = []
    for i, proxy_image in enumerate(zstack_proxy_iterator):
        image = proxy_image.image
        segmented = segment_zslice(image)
        with open("z{:03d}.png".format(i), "wb") as fh:
            fh.write(segmented.png())
        with open("raw_z{:03d}.png".format(i), "wb") as fh:
            fh.write(image.png())
        raw.append(image)
        zstack.append(segmented)
    return np.dstack(raw), np.dstack(zstack)


def segment(zstack_proxy_iterator):
    """Return a segmented image."""
    raw, processed = preprocess_zstack(zstack_proxy_iterator, 90)
    projection = max_intensity_projection(raw)
    binary_wall = max_intensity_projection(processed)
    image = dilate_binary(binary_wall)
    image = invert(image)
    image = remove_small_objects(image, min_size=10)
    seeds = connected_components(image, background=0)
    segmentation = watershed_with_seeds(-projection, seeds=seeds)

    return segmentation, projection


def annotate(segmentation, projection):
    """Write out an annotated image."""
    ann = AnnotatedImage.from_grayscale(projection)
    for i in segmentation.identifiers:
        region = segmentation.region_by_identifier(i)
        ann.mask_region(region.inner.border.dilate(), color=pretty_color(i))
    with open("annotation.png", "wb") as fh:
        fh.write(ann.png())


def main():
    """Run the analysis on an indivudual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)
    zstack_proxy_iterator = microscopy_collection.zstack_proxy_iterator(c=1)

    segmentation, projection = segment(zstack_proxy_iterator)
    annotate(segmentation, projection)

if __name__ == "__main__":
    main()
