"""Basic webapp for editing tensors."""

import os.path
import argparse
import PIL
from flask import Flask, render_template, url_for, request
from tensor import TensorManager

from utils import HERE

app = Flask(__name__)

@app.route("/")
def index():
    im_fname = "segmentation.png"
    im_fpath = os.path.join(HERE, "static", im_fname)
    im = PIL.Image.open(im_fpath)
    xdim, ydim = im.size
    tensors = [tensor_manager[i] for i in app.tensor_manager.identifiers]
    return render_template("template.html",
                           xdim=xdim,
                           ydim=ydim,
                           tensors=tensors,
                           raster_fname=url_for("static", filename=im_fname))

@app.route("/inactivate_tensor/<int:tensor_id>", methods=["POST"])
def inactivate_tensor(tensor_id):
    if request.method == "POST":
        app.tensor_manager.inactivate_tensor(tensor_id)
        app.logger.debug("Inactivated tensor {:d}".format(tensor_id))
    return "Inactivated tensor {:d}\n".format(tensor_id)

@app.route("/audit_log")
def audit_log():
    return render_template("audit_log.html",
                           tensor_manager=app.tensor_manager)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_tensors", help="path to file")
    args = parser.parse_args()

    if not os.path.isfile(args.raw_tensors):
        parser.error("No such file {}".format(args.raw_tensors))

    tensor_manager = TensorManager()
    with open(args.raw_tensors) as fh:
        tensor_manager.read_raw_tensors(fh)
    app.tensor_manager = tensor_manager

    app.run(debug=True)
