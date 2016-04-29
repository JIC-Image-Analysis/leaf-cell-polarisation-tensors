"""Module for creating SVG figure."""

import os
from jinja2 import Environment, FileSystemLoader

from utils import HERE

env = Environment(loader=FileSystemLoader(HERE))
svg_template = env.get_template("template.svg")
svg_template = env.get_template("template.html")


def write_svg(ydim, xdim, tensor_manager, raster_fname, fh):
    """Write out an SVG illustration."""
    tensors = [tensor_manager[i] for i in tensor_manager.identifiers]
    fh.write(svg_template.render(xdim=xdim,
                                 ydim=ydim,
                                 tensors=tensors,
                                 raster_fname=raster_fname))

def write_html(ydim, xdim, tensor_manager, raster_fname, fh):
    """Write out HTML with inlined SVG illustration."""
    tensors = [tensor_manager[i] for i in tensor_manager.identifiers]
    fh.write(html_template.render(xdim=xdim,
                                  ydim=ydim,
                                  tensors=tensors,
                                  raster_fname=raster_fname))

if __name__ == "__main__":
    from tensor import TensorManager
    ydim, xdim = 1362, 836
    tensors = TensorManager()
    with open("raw_tensors.txt") as fh:
        tensors.read_raw_tensors(fh)
    with open("test.svg", "w") as fh:
        write_svg(ydim, xdim, tensors, "segmentation.png", fh)
    with open("test.html", "w") as fh:
        write_svg(ydim, xdim, tensors, "segmentation.png", fh)
