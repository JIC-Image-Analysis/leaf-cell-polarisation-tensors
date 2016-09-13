"""Generate cells for validation."""

import os
import argparse
from functools import wraps
import random

import numpy as np
import scipy.ndimage

from jicbioimage.core.io import AutoName, AutoWrite
from jicbioimage.core.util.color import pretty_color_from_identifier
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection
from segment import segment
from tensor import get_tensors


def best_tensor(cell_tensors, markers):
    """Return the tensor associated with the largest marker area."""
    largest_area_tensor = None
    largest_area = None
    for i, t in enumerate(cell_tensors):
        marker_region = markers.region_by_identifier(t.tensor_id)
        area = marker_region.area
        if largest_area is None:
            largest_area_tensor = t
            largest_area = area
        elif area > largest_area:
            largest_area_tensor = t
            largest_area = area
    return largest_area_tensor


def post_process_annotation(ann, cell_tensors, dilated_region, crop=True,
                            rotation=None, enlarge=True, padding=True):

    if crop:
        yis, xis = dilated_region.index_arrays
        ann = ann[np.min(yis):np.max(yis),
                  np.min(xis):np.max(xis)]

    if padding:
        ydim, xdim, zdim = ann.shape
        p = 25
        pydim = ydim + p + p
        pxdim = xdim + p + p
        padded = AnnotatedImage.blank_canvas(width=pxdim, height=pydim)
        padded[p:ydim+p, p:xdim+p] = ann
        ann = padded

    if enlarge:
        ann = scipy.misc.imresize(ann, 3.0, "nearest").view(AnnotatedImage)

    if rotation:
        ann = scipy.ndimage.rotate(ann, rotation).view(AnnotatedImage)

    return ann


def write_annotations(fpath_prefix, wall_projection, marker_projection, region,
                      cell_tensors, markers, crop=True, rotation=None,
                      enlarge=True, padding=True, draw_all=False):
    wall_ann = AnnotatedImage.from_grayscale(wall_projection, (1, 0, 0))
    marker_ann = AnnotatedImage.from_grayscale(marker_projection, (0, 1, 0))
    ann = wall_ann + marker_ann
    ann.mask_region(region.border, (200, 200, 200))
    dilated_region = region.dilate(20)
    ann[np.logical_not(dilated_region)] = (0, 0, 0)

    for t in cell_tensors:
        if draw_all:
            ann.draw_line(t.centroid, t.marker, color=(200, 200, 0))

    largest_area_tensor = best_tensor(cell_tensors, markers)
    if largest_area_tensor:
        ann.draw_line(largest_area_tensor.centroid,
                      largest_area_tensor.marker,
                      color=(200, 0, 200))

    for suffix, annotation in [("-wall", wall_ann),
                               ("-marker", marker_ann),
                               ("-combined", ann)]:
        fpath = fpath_prefix + suffix + ".png"
        annotation = post_process_annotation(annotation, cell_tensors,
                                             dilated_region, crop, rotation,
                                             enlarge, padding)

        with open(fpath, "wb") as fh:
            fh.write(annotation.png())


def marker_area(tensor, markers):
    """Return marker area for a particular tensor."""
    tensor_id = tensor.tensor_id
    region = markers.region_by_identifier(tensor_id)
    return region.area


def generate_cells_for_validation(microscopy_collection, wall_channel,
                                  marker_channel, fprefix,
                                  include_cells_with_no_tensors=True,
                                  crop=True,
                                  rotate=True,
                                  enlarge=True,
                                  padding=True):
    """Generate PNG files for validation."""
    (cells,
     markers,
     wall_projection,
     marker_projection) = segment(microscopy_collection, wall_channel,
                                  marker_channel)

    tensors = get_tensors(cells, markers)

    no_tensor_dir = os.path.join(AutoName.directory, "none")
    single_tensor_dir = os.path.join(AutoName.directory, "single")
    multi_tensor_dir = os.path.join(AutoName.directory, "multi")
    for d in [no_tensor_dir, single_tensor_dir, multi_tensor_dir]:
        if not os.path.isdir(d):
            os.mkdir(d)

    for cell_id in tensors.cell_identifiers:
        rotation = None
        if rotate:
            rotation = random.randrange(0, 360)

        cell_tensors = tensors.cell_tensors(cell_id)
        region = cells.region_by_identifier(cell_id)

        fmiddle = "-cell-{:03d}".format(cell_id)
        png_fname = fprefix + fmiddle
        csv_fname = fprefix + fmiddle + ".csv"

        num_tensors = len(cell_tensors)
        if num_tensors > 0:
            largest_area_tensor = best_tensor(cell_tensors, markers)
            fpath = os.path.join(single_tensor_dir, csv_fname)
            with open(fpath, "w") as fh:
                fh.write("{},{}\n".format(largest_area_tensor.csv_line, rotation))

            fpath = os.path.join(single_tensor_dir, png_fname)
            write_annotations(fpath, wall_projection, marker_projection, region,
                              cell_tensors, markers, crop, rotation, enlarge,
                              padding)

        if num_tensors > 1:
            fpath = os.path.join(multi_tensor_dir, png_fname)
            write_annotations(fpath, wall_projection, marker_projection, region,
                              cell_tensors, markers, crop, rotation,
                              enlarge, padding, draw_all=True)

    if include_cells_with_no_tensors:
        for cell_id in cells.identifiers:
            if cell_id in tensors.cell_identifiers:
                continue
            region = cells.region_by_identifier(cell_id)
            cell_tensors = tensors.cell_tensors(cell_id)
            assert len(cell_tensors) == 0
            fname = fprefix + "-cell-{:03d}".format(cell_id)
            fpath = os.path.join(no_tensor_dir, fname)
            write_annotations(fpath, wall_projection, marker_projection, region,
                              cell_tensors, crop, rotation, enlarge,
                              padding)


def analyse_file(fpath, wall_channel, marker_channel,
                 include_cells_with_no_tensors,
                 crop, rotate, enlarge, padding):
    """Analyse a single file."""
    microscopy_collection = get_microscopy_collection(fpath)
    fprefix = os.path.basename(fpath)
    fprefix, _ = os.path.splitext(fprefix)
    generate_cells_for_validation(microscopy_collection, wall_channel,
                                  marker_channel, fprefix,
                                  include_cells_with_no_tensors,
                                  crop, rotate, enlarge, padding)


def analyse_directory(input_directory, wall_channel, marker_channel,
                      include_cells_with_no_tensors,
                      crop, rotate, enlarge, padding, output_directory):
    """Analyse all the files in a directory."""
    for fname in os.listdir(input_directory):
        name, ext = os.path.splitext(fname)
        AutoName.directory = os.path.join(output_directory, name)
        if not os.path.isdir(AutoName.directory):
            os.mkdir(AutoName.directory)
        fpath = os.path.join(input_directory, fname)
        analyse_file(fpath, wall_channel, marker_channel,
                     include_cells_with_no_tensors,
                     crop, rotate, enlarge, padding)


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
    parser.add_argument("-e", "--exclude-cells-with-no-tensors", action="store_true")
    parser.add_argument("--no-crop", action="store_true")
    parser.add_argument("--no-rotation", action="store_true")
    parser.add_argument("--no-enlarge", action="store_true")
    parser.add_argument("--no-padding", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    AutoWrite.on = args.debug

    # Create the output directory if it does not exist.
    if not os.path.isdir(args.output_dir):
        os.mkdir(args.output_dir)
    AutoName.directory = args.output_dir

    # Run the analysis.
    if os.path.isfile(args.input_source):
        analyse_file(args.input_source, args.wall_channel, args.marker_channel,
                     include_cells_with_no_tensors=not args.exclude_cells_with_no_tensors,
                     crop=not args.no_crop,
                     rotate=not args.no_rotation,
                     enlarge=not args.no_enlarge,
                     padding=not args.no_padding)
    elif os.path.isdir(args.input_source):
        analyse_directory(args.input_source, args.wall_channel,
                          args.marker_channel,
                          include_cells_with_no_tensors=not args.exclude_cells_with_no_tensors,
                          crop=not args.no_crop,
                          rotate=not args.no_rotation,
                          enlarge=not args.no_enlarge,
                          padding=not args.no_padding,
                          output_directory=args.output_dir)
    else:
        parser.error("{} not a file or directory".format(args.input_source))


if __name__ == "__main__":
    main()
