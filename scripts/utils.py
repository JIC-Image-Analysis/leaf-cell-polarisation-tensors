"""Utility functions."""

import os.path

import numpy as np

from jicbioimage.core.image import MicroscopyCollection
from jicbioimage.core.transform import transformation
from jicbioimage.core.io import (
    AutoWrite,
    FileBackend,
    DataManager,
    _md5_hexdigest_from_file,
)
from jicbioimage.transform import (
    remove_small_objects,
    max_intensity_projection,
)

HERE = os.path.dirname(os.path.realpath(__file__))


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


def get_wall_intensity_and_mask_images(microscopy_collection):
    """
    Return (wall_intensity2D, wall_intensity3D, wall_mask2D, wall_mask3D).
    """
    wall_ziter = microscopy_collection.zstack_proxy_iterator(c=1)
    wall_intensity3D, wall_mask3D = preprocess_zstack(wall_ziter, 90)
    wall_intensity2D = max_intensity_projection(wall_intensity3D)
    wall_mask2D = max_intensity_projection(wall_mask3D)
    return wall_intensity2D, wall_intensity3D, wall_mask2D, wall_mask3D


def get_marker_intensity_images(microscopy_collection):
    """REturn (marker_intensity2D, marker_intensity3D) tuple."""
    marker_intensity3D = microscopy_collection.zstack_array(c=0)
    marker_intensity2D = max_intensity_projection(marker_intensity3D)
    return marker_intensity2D, marker_intensity3D


def marker_cell_identifier(marker_region, cells):
    """Return cell identifier of marker region."""
    pos = marker_region.convex_hull.centroid
    return cells[pos]
