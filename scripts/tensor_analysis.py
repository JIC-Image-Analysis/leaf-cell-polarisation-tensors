"""Analyse the polarity of cells using tensors."""

import os.path
import argparse

import numpy as np
import skimage.draw

from jicbioimage.core.image import MicroscopyCollection
from jicbioimage.core.transform import transformation
from jicbioimage.core.util.color import pretty_color
from jicbioimage.core.io import (
    AutoWrite,
    AutoName,
    FileBackend,
    DataManager,
    _md5_hexdigest_from_file,
)
from jicbioimage.transform import (
    max_intensity_projection,
    remove_small_objects,
    dilate_binary,
    invert,
)
from jicbioimage.segment import (
    connected_components,
    watershed_with_seeds,
)
from jicbioimage.illustrate import AnnotatedImage

HERE = os.path.dirname(os.path.realpath(__file__))
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


def get_microscopy_collection(input_file):
    """Return microscopy collection from input file."""
    data_dir = os.path.abspath(os.path.join(HERE, "..", "data"))
    if not os.path.isdir(data_dir):
        raise(OSError("Data directory does not exist: {}".format(data_dir)))
    backend_dir = os.path.join(data_dir, 'unpacked')
    file_backend = FileBackend(backend_dir)
    data_manager = DataManager(file_backend)
    data_manager.load(input_file)

    md5_hex = _md5_hexdigest_from_file(input_file)
    manifest_path = os.path.join(backend_dir, md5_hex, "manifest.json")

    microscopy_collection = MicroscopyCollection()
    microscopy_collection.parse_manifest(manifest_path)
    return microscopy_collection


@transformation
def identity(image):
    return image


@transformation
def threshold_abs(image, threshold):
    """Return image thresholded using the mean."""
    return image > threshold


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
        raw.append(image)
        zstack.append(segmented)
    return np.dstack(raw), np.dstack(zstack)


def cell_segmentation(wall_intensity2D, wall_mask2D):
    """Return image segmented into cells."""
    seeds = dilate_binary(wall_mask2D)
    seeds = invert(seeds)
    seeds = remove_small_objects(seeds, min_size=10)
    seeds = connected_components(seeds, background=0)
    return watershed_with_seeds(-wall_intensity2D, seeds=seeds)


def marker_segmentation(marker_intensity3D, wall_mask3D):
    """Return fluorescent marker segmentation."""
    marker_intensity3D = marker_intensity3D * wall_mask3D
    markers2D = max_intensity_projection(marker_intensity3D)
    markers2D = threshold_abs(markers2D, 45)
    markers2D = remove_small_objects(markers2D, min_size=50)
    return connected_components(markers2D, background=0)


def marker_cell_identifier(marker_region, cells):
    """Return cell identifier of marker region."""
    pos = marker_region.convex_hull.centroid
    return cells[pos]


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
    wall_ziter = microscopy_collection.zstack_proxy_iterator(c=1)
    wall_intensity3D, wall_mask3D = preprocess_zstack(wall_ziter, 90)
    wall_intensity2D = max_intensity_projection(wall_intensity3D)
    wall_mask2D = max_intensity_projection(wall_mask3D)
    marker_intensity3D = microscopy_collection.zstack_array(c=0)
    marker_intensity2D = max_intensity_projection(marker_intensity3D)

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
