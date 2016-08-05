"""Module for creating annotated images."""

import PIL

from jicbioimage.core.util.color import pretty_color_from_identifier
from jicbioimage.illustrate import AnnotatedImage

from utils import marker_cell_identifier


def annotate_segmentation(cells, fh):
    """Write out segmentation image."""
    fh.write(cells.png())


def annotate_markers(markers, cells, fh):
    """Write out marker image."""
    ydim, xdim = markers.shape
    ann = AnnotatedImage.blank_canvas(width=xdim, height=ydim)
    for i in markers.identifiers:
        m_region = markers.region_by_identifier(i)
        cell_id = marker_cell_identifier(m_region, cells)
        color = pretty_color_from_identifier(cell_id)
        ann.mask_region(m_region, color)
    fh.write(ann.png())


def annotate_tensors(ydim, xdim, tensor_manager, fh):
    """Write out tensor image."""
    ann = AnnotatedImage.blank_canvas(width=xdim, height=ydim)
    for i in tensor_manager.identifiers:
        tensor = tensor_manager[i]
        color = pretty_color_from_identifier(tensor.cell_id)
        ann.draw_line(tensor.centroid, tensor.marker, color)
    fh.write(ann.png())


def make_transparent(pil_im, alpha):
    """Return rgba pil image."""
    pil_im = pil_im.convert("RGBA")
    pixdata = pil_im.load()
    for y in xrange(pil_im.size[1]):
        for x in xrange(pil_im.size[0]):
            rgba = list(pixdata[x, y])
            rgba[-1] = alpha
            pixdata[x, y] = tuple(rgba)
    return pil_im
