import os
import argparse

import skimage.filters

from jicbioimage.core.io import AutoName, AutoWrite
from jicbioimage.core.util.color import pretty_color_from_identifier
from jicbioimage.core.transform import transformation
from jicbioimage.transform import (
    invert,
    dilate_binary,
    remove_small_objects,
)
from jicbioimage.segment import connected_components, watershed_with_seeds
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection
from gaussproj import (
    generate_surface_from_stack,
    projection_from_stack_and_surface,
)

AutoName.prefix_format = "{:03d}_"


@transformation
def identity(image):
    return image


@transformation
def threshold_adaptive_median(image, block_size):
    return skimage.filters.threshold_adaptive(image, block_size=block_size)


@transformation
def remove_large_segments(segmentation, max_size):
    for i in segmentation.identifiers:
        region = segmentation.region_by_identifier(i)
        if region.area > max_size:
            segmentation[region] = 0
    return segmentation


@transformation
def marker_in_wall(marker, wall):
    return marker * wall


@transformation
def threshold_abs(image, threshold):
    return image > threshold


def segment_cells(image, max_cell_size):
    """Return segmented cells and binary wall mask."""
    image = identity(image)

    wall_mask = threshold_adaptive_median(image, block_size=101)
    wall_mask = remove_small_objects(wall_mask, min_size=100)
    wall_mask = dilate_binary(wall_mask)

    seeds = invert(wall_mask)
    seeds = remove_small_objects(seeds, min_size=5)
    seeds = connected_components(seeds, background=0)

    segmentation = watershed_with_seeds(-image, seeds=seeds)
    segmentation = remove_large_segments(segmentation, max_cell_size)
    return segmentation, wall_mask


def segment_markers(image, wall_mask, min_size, threshold):
    """Return segmented markers."""
    image = identity(image)

    image = threshold_abs(image, threshold)
    image = marker_in_wall(image, wall_mask)
    image = remove_small_objects(image, min_size=min_size)

    segmentation = connected_components(image, background=0)
    return segmentation


def segment(microscopy_collection, wall_channel, marker_channel):
    """Return cell and marker segmentations."""
    wall_stack = microscopy_collection.zstack_array(c=wall_channel)
    marker_stack = microscopy_collection.zstack_array(c=marker_channel)

    surface = generate_surface_from_stack(wall_stack)
    wall_projection = projection_from_stack_and_surface(wall_stack,
                                                        surface)
    marker_projection = projection_from_stack_and_surface(marker_stack,
                                                          surface)

    cells, wall_mask = segment_cells(wall_projection, max_cell_size=10000)
    markers = segment_markers(marker_projection, wall_mask, min_size=5,
                              threshold=70)

    return cells, markers, wall_projection, marker_projection


def generate_segmentations(microscopy_collection, wall_channel,
                           marker_channel, fprefix):
    """Generate cell-segmentation.png and marker-segmentation.png files."""
    (cells,
     markers,
     wall_projection,
     marker_projection) = segment(microscopy_collection, wall_channel,
                                  marker_channel)

    def get_ann(segmentation, projection):
        ann = AnnotatedImage.from_grayscale(projection)
        for i in segmentation.identifiers:
            color = pretty_color_from_identifier(i)
            region = segmentation.region_by_identifier(i)
            ann.mask_region(region.border, color)
        return ann

    ann = get_ann(cells, wall_projection)
    fpath = os.path.join(AutoName.directory, fprefix + "-cell-segmentation.png")
    with open(fpath, "wb") as fh:
        fh.write(ann.png())

    ann = get_ann(markers, marker_projection)
    fpath = os.path.join(AutoName.directory, fprefix + "-marker-segmentation.png")
    with open(fpath, "wb") as fh:
        fh.write(ann.png())


def analyse_file(fpath, wall_channel, marker_channel):
    """Analyse a single file."""
    microscopy_collection = get_microscopy_collection(fpath)
    fprefix = os.path.basename(fpath)
    fprefix, _ = os.path.splitext(fprefix)
    generate_segmentations(microscopy_collection, wall_channel, marker_channel, fprefix)


def analyse_directory(input_directory, wall_channel, marker_channel):
    """Analyse all the files in a directory."""
    for fname in os.listdir(input_directory):
        fpath = os.path.join(input_directory, fname)
        analyse_file(fpath, wall_channel, marker_channel)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_source', help="Input file / directory.")
    parser.add_argument("output_dir", help="Output directory")
    parser.add_argument("-w", "--wall-channel",
                        default=1, type=int,
                        help="Wall channel (zero indexed)")
    parser.add_argument("-m", "--marker-channel",
                        default=0, type=int,
                        help="Marker channel (zero indexed)")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    AutoWrite.on = args.debug

    # Create the output directory if it does not exist.
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    AutoName.directory = args.output_dir

    # Run the analysis.
    if os.path.isfile(args.input_source):
        analyse_file(args.input_source, args.wall_channel, args.marker_channel)
    elif os.path.isdir(args.input_source):
        analyse_directory(args.input_source, args.wall_channel,
                          args.marker_channel)
    else:
        parser.error("{} not a file or directory".format(args.input_source))


if __name__ == "__main__":
    main()
