"""Segment leaf into individual cells."""

import os.path
import argparse
import warnings

from jicbioimage.core.util.color import pretty_color
from jicbioimage.transform import (
    max_intensity_projection,
    remove_small_objects,
    invert,
    dilate_binary,
)
from jicbioimage.segment import connected_components, watershed_with_seeds
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection, preprocess_zstack

# Suppress spurious scikit-image warnings.
warnings.filterwarnings("ignore", module="skimage.io._io")


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
