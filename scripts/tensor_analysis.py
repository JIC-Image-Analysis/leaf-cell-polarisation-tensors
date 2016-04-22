"""Analyse the polarity of cells using tensors."""

import os.path
import argparse

import numpy as np
import skimage.draw

from jicbioimage.core.util.color import pretty_color
from jicbioimage.core.io import (
    AutoName,
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

AutoName.prefix_format = "{:03d}_"


class CellTensor(object):
    """Class for storing cell identifier, centroid and marker position."""
    def __init__(self, identifier, centroid, marker_position):
        self.identifier = identifier
        self.centroid = centroid
        self.marker_position = marker_position

    @staticmethod
    def csv_header():
        """Return CSV header line."""
        return "cell_id,mx,my,cx,cy\n"

    @classmethod
    def from_csv_line(cls, line):
        """Return CellTensor instance from a CSV line."""
        line = line.strip()
        words = line.split(",")
        identifier = int(words[0])
        marker_position = (float(words[2]), float(words[1]))
        centroid = (float(words[4]), float(words[3]))
        return cls(identifier, centroid, marker_position)

    @property
    def csv_line(self):
        """Return CellTensor as a CSV line."""
        line = "{:d},{:f},{:f},{:f},{:f}\n"
        return line.format(self.identifier,
                           self.marker_position[1],  # x
                           self.marker_position[0],  # y
                           self.centroid[1],  # x
                           self.centroid[0],  # y
                           )


def yield_cell_tensors(cells, markers):
    """Return cell tensor iterator."""
    for i in markers.identifiers:
        m_region = markers.region_by_identifier(i)
        marker_position = m_region.convex_hull.centroid
        cell_id = marker_cell_identifier(m_region, cells)
        c_region = cells.region_by_identifier(cell_id)
        centroid = c_region.centroid
        yield CellTensor(cell_id, centroid, marker_position)


def line_mask(shape, pos1, pos2):
    """Return line mask for annotating images."""
    line = np.zeros(shape, dtype=bool)
    y0, x0 = tuple([int(round(i)) for i in pos1])
    y1, x1 = tuple([int(round(i)) for i in pos2])
    rows, cols = skimage.draw.line(y0, x0, y1, x1)
    line[rows, cols] = True
    return line


def annotate(cells, markers, wall_intensity2D, marker_intensity2D):
    """Write an annotated image to disk."""
    ann = AnnotatedImage.from_grayscale(wall_intensity2D/5,
                                        (True, False, True))
    ann = ann + AnnotatedImage.from_grayscale(marker_intensity2D,
                                              (False, True, False))

    for i in cells.identifiers:
        region = cells.region_by_identifier(i)
        ann.mask_region(region.border, color=pretty_color(i))

    for i in markers.identifiers:
        m_region = markers.region_by_identifier(i)
        cell_id = marker_cell_identifier(m_region, cells)
        color = pretty_color(cell_id)
        ann.mask_region(m_region.border, color=color)

    for cell_tensor in yield_cell_tensors(cells, markers):
        color = pretty_color(cell_tensor.identifier)
        ydim, xdim, zdim = ann.shape
        line = line_mask((ydim, xdim), cell_tensor.marker_position,
                         cell_tensor.centroid)
        ann.mask_region(line, color=color)

    with open("annotation.png", "wb") as fh:
        fh.write(ann.png())


def annotate_simple(wall_mask2D, cells, markers):
    """Write an annotated image to disk."""
    y, x = wall_mask2D.shape
    ann1 = AnnotatedImage.blank_canvas(width=x, height=y)
    ann1.mask_region(wall_mask2D, (55, 55, 55))

    ann2 = AnnotatedImage.blank_canvas(width=x, height=y)
    ann2.mask_region(wall_mask2D, (0, 0, 0))

    for i in markers.identifiers:
        m_region = markers.region_by_identifier(i)
        cell_id = marker_cell_identifier(m_region, cells)
        color = pretty_color(cell_id)
        ann1.mask_region(m_region, color=color)

    for cell_tensor in yield_cell_tensors(cells, markers):
        color = pretty_color(cell_tensor.identifier)
        ydim, xdim, zdim = ann1.shape
        line = line_mask((ydim, xdim), cell_tensor.marker_position,
                         cell_tensor.centroid)
        ann1.mask_region(line, color=color)
        ann2.mask_region(line, color=color)
        ann1.draw_cross(cell_tensor.centroid, color=color)
        ann2.draw_cross(cell_tensor.centroid, color=color)

    with open("simple_ann1.png", "wb") as fh:
        fh.write(ann1.png())

    with open("simple_ann2.png", "wb") as fh:
        fh.write(ann2.png())


def write_tensor_csv(cells, markers):
    """Write out a tensors.csv file."""
    with open("tensors.csv", "w") as fh:
        fh.write(CellTensor.csv_header())
        for cell_tensor in yield_cell_tensors(cells, markers):
            fh.write(cell_tensor.csv_line)


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

    # Create annotated images.
    annotate(cells, markers, wall_intensity2D, marker_intensity2D*wall_mask2D)
    annotate_simple(wall_mask2D, cells, markers)

    # Write out csv file.
    write_tensor_csv(cells, markers)


def main():
    """Run the analysis on an individual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)
    analyse(microscopy_collection)


if __name__ == "__main__":
    main()
