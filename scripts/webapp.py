"""Basic webapp for editing tensors."""

import os.path
import argparse
import PIL
from flask import Flask, render_template, url_for
from tensor import TensorManager

from utils import HERE

app = Flask(__name__)

@app.route("/")
def index():
    im_fname = "segmentation.png"
    im_fpath = os.path.join(HERE, "static", im_fname)
    im = PIL.Image.open(im_fpath)
    xdim, ydim = im.size
    return render_template("template.html",
                           xdim=xdim,
                           ydim=ydim,
                           tensors=app.tensors,
                           raster_fname=url_for("static", filename=im_fname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_tensors", help="path to file")
    args = parser.parse_args()

    if not os.path.isfile(args.raw_tensors):
        parser.error("No such file {}".format(args.raw_tensors))

    tensor_manager = TensorManager()
    with open(args.raw_tensors) as fh:
        tensor_manager.read_raw_tensors(fh)
    tensors = [tensor_manager[i] for i in tensor_manager.identifiers]
    app.tensors = tensors

    app.run(debug=True)
