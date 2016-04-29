"""Basic webapp for editing tensors."""

from flask import Flask, render_template, url_for
from tensor import TensorManager

app = Flask(__name__)

# For testing.
ydim, xdim = 1362, 836
tensor_manager = TensorManager()
with open("raw_tensors.txt") as fh:
    tensor_manager.read_raw_tensors(fh)
tensors = [tensor_manager[i] for i in tensor_manager.identifiers]

@app.route("/")
def index():
    return render_template("template.html",
                           xdim=xdim,
                           ydim=ydim,
                           tensors=tensors,
                           raster_fname=url_for("static", filename="segmentation.png"))


if __name__ == "__main__":
    app.run(debug=True)
