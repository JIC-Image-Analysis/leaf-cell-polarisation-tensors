"""Generate cells for validation."""

import os
import argparse

import numpy as np

from jicbioimage.core.io import AutoName, AutoWrite
from jicbioimage.illustrate import AnnotatedImage

from utils import get_microscopy_collection
from segment import segment
from tensor import get_tensors

def annotated_region(wall_projection, marker_projection, region, cell_tensors):
    wall_ann = AnnotatedImage.from_grayscale(wall_projection, (1, 0, 0))
    marker_ann = AnnotatedImage.from_grayscale(marker_projection, (0, 1, 0))
    ann = wall_ann + marker_ann

    for t in cell_tensors:
        ann.draw_line(t.centroid, t.marker)

    ann[np.logical_not(region)] = (0, 0, 0)
    return ann


def generate_cells_for_validation(microscopy_collection, wall_channel,
                                  marker_channel, fprefix):
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
        cell_tensors = tensors.cell_tensors(cell_id)
        region = cells.region_by_identifier(cell_id)
        ann = annotated_region(wall_projection, marker_projection, region,
                               cell_tensors)

        num_tensors = len(cell_tensors)
        if num_tensors == 1:
            fname = fprefix + "-cell-{:03d}.png".format(cell_id)
            fpath = os.path.join(single_tensor_dir, fname)
        elif num_tensors > 1:
            fname = fprefix + "-cell-{:03d}.png".format(cell_id)
            fpath = os.path.join(multi_tensor_dir, fname)

        with open(fpath, "wb") as fh:
            fh.write(ann.png())

    for cell_id in cells.identifiers:
        if cell_id in tensors.cell_identifiers:
            continue
        cell_tensors = tensors.cell_tensors(cell_id)
        region = cells.region_by_identifier(cell_id)
        ann = annotated_region(wall_projection, marker_projection, region,
                               cell_tensors)
        num_tensors = len(cell_tensors)
        assert num_tensors == 0

        fname = fprefix + "-cell-{:03d}.png".format(cell_id)
        fpath = os.path.join(no_tensor_dir, fname)
        with open(fpath, "wb") as fh:
            fh.write(ann.png())

def analyse_file(fpath, wall_channel, marker_channel):
    """Analyse a single file."""
    microscopy_collection = get_microscopy_collection(fpath)
    fprefix = os.path.basename(fpath)
    fprefix, _ = os.path.splitext(fprefix)
    generate_cells_for_validation(microscopy_collection, wall_channel,
                                  marker_channel, fprefix)


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
