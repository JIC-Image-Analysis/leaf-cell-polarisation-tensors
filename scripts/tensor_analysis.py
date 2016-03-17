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
    Region,
    connected_components,
    watershed_with_seeds,
)
from jicbioimage.illustrate import AnnotatedImage

HERE = os.path.dirname(os.path.realpath(__file__))
AutoName.prefix_format = "{:03d}_"


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

def annotate(cells, markers, intensity):
    """Write an annotated image to disk."""
    ann = AnnotatedImage.from_grayscale(intensity)

    for i in cells.identifiers:
        region = cells.region_by_identifier(i)
        ann.mask_region(region.border, color=pretty_color(i))

    for i in markers.identifiers:
        m_region = markers.region_by_identifier(i)
        m_centroid = m_region.convex_hull.centroid

        cell_id = marker_cell_identifier(m_region, cells)
        c_region = cells.region_by_identifier(cell_id)
        c_centroid = c_region.centroid

        color = pretty_color(cell_id)
        ann.mask_region(m_region.border, color=color)

#       try:
#           ann.draw_cross(m_region.convex_hull.centroid, color=color)
#       except IndexError:
#           print "Issue with marker region {} centroid {}".format(i, m_region.convex_hull.centroid)

#       try:
#           ann.draw_cross(c_region.centroid, color=color)
#       except IndexError:
#           print "Issue with cell region {} centroid {}".format(cell_id, m_region.centroid)

        ydim, xdim, zdim = ann.shape
        line = np.zeros((ydim, xdim), dtype=bool)
        y0, x0 = tuple([int(round(i)) for i in m_centroid])
        y1, x1 = tuple([int(round(i)) for i in c_centroid])
        rows, cols = skimage.draw.line(y0, x0, y1, x1)
        line[rows, cols] = True
        ann.mask_region(line, color=color)

    with open("annotation.png", "wb") as fh:
        fh.write(ann.png())


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
    annotate(cells, markers, marker_intensity2D)


def main():
    """Run the analysis on an indivudual image."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", help="Path to input tiff file")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)
    analyse(microscopy_collection)


if __name__ == "__main__":
    main()
