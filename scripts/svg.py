"""Module for creating SVG figure."""

import os
from jinja2 import Environment, FileSystemLoader

from utils import HERE

env = Environment(loader=FileSystemLoader(HERE))
svg_template = env.get_template("template.svg")


def write_svg(ydim, xdim, tensor_manager, raster_fname, fh):
    """Write out an SVG illustration."""
    tensors = [tensor_manager[i] for i in tensor_manager.identifiers]
    fh.write(svg_template.render(xdim=xdim,
                                 ydim=ydim,
                                 tensors=tensors,
                                 raster_fname=raster_fname))
