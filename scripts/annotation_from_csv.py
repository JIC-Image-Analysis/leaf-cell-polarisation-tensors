import os
import argparse

from jicbioimage.transform import max_intensity_projection
from jicbioimage.core.util.color import pretty_color

from tensor_analysis import (
    CellTensor,
    get_microscopy_collection,
    preprocess_zstack,
    line_mask,
)

from jicbioimage.illustrate import AnnotatedImage


def yield_cell_tensors_from_csv(input_csv):
    """Yeild cell tensors from csv file."""
    with open(input_csv) as fh:
        fh.next()  # Ignore header line.
        for line in fh:
            yield CellTensor.from_csv_line(line)


def annotation_from_csv(microscopy_collection, input_csv):
    """Annotate image using tensors from input CSV file."""
    wall_ziter = microscopy_collection.zstack_proxy_iterator(c=1)
    wall_intensity3D, wall_mask3D = preprocess_zstack(wall_ziter, 90)
    wall_mask2D = max_intensity_projection(wall_mask3D)

    y, x = wall_mask2D.shape
    ann = AnnotatedImage.blank_canvas(width=x, height=y)
    ann.mask_region(wall_mask2D, (55, 55, 55))

    for cell_tensor in yield_cell_tensors_from_csv(input_csv):
        color = pretty_color(cell_tensor.identifier)
        ydim, xdim, zdim = ann.shape
        line = line_mask((ydim, xdim), cell_tensor.marker_position,
                         cell_tensor.centroid)
        ann.mask_region(line, color=color)
        ann.draw_cross(cell_tensor.centroid, color=color)

    with open("annotation.png", "wb") as fh:
        fh.write(ann.png())


def main():
    """Run the analysis on an individual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_tiff", help="Path to input tiff file")
    parser.add_argument("input_csv", help="Path to input csv file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_tiff):
        parser.error("No such file: {}".format(args.input_tiff))
    if not os.path.isfile(args.input_csv):
        parser.error("No such file: {}".format(args.input_csv))

    microscopy_collection = get_microscopy_collection(args.input_tiff)
    annotation_from_csv(microscopy_collection, args.input_csv)


if __name__ == "__main__":
    main()
