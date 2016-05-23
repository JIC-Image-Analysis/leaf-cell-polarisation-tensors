"""Module for segmenting cells and markers."""

from jicbioimage.transform import (
    dilate_binary,
    invert,
    remove_small_objects,
    max_intensity_projection,
)
from jicbioimage.segment import (
    connected_components,
    watershed_with_seeds,
)

from utils import threshold_abs


def cell_segmentation(wall_intensity2D, wall_mask2D):
    """Return image segmented into cells."""
    seeds = dilate_binary(wall_mask2D)
    seeds = invert(seeds)
    seeds = remove_small_objects(seeds, min_size=10)
    seeds = connected_components(seeds, background=0)
    return watershed_with_seeds(-wall_intensity2D, seeds=seeds)


def marker_segmentation(marker_intensity3D, wall_mask3D, threshold):
    """Return fluorescent marker segmentation."""
    marker_intensity3D = marker_intensity3D * wall_mask3D
    markers2D = max_intensity_projection(marker_intensity3D)
    markers2D = threshold_abs(markers2D, threshold)
    markers2D = remove_small_objects(markers2D, min_size=50)
    return connected_components(markers2D, background=0)
