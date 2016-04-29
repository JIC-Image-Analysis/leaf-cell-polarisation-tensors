var selected = null;

function toggleSegmentation() {
  var visibility = document.getElementById("segmentation").getAttribute("visibility");
  if (!visibility) {
    document.getElementById("segmentation").setAttribute("visibility", "hidden");
  }
  else if (visibility == "hidden") {
    document.getElementById("segmentation").setAttribute("visibility", "visible");
  }
  else {
    document.getElementById("segmentation").setAttribute("visibility", "hidden");
  }
}

function showElement() {
  document.getElementById(this.id).setAttribute("fill", "red");
}

function hideElement() {
  if (selected != this.id) {
    document.getElementById(this.id).setAttribute("fill", "black");
  }
}

function selectElement(event) {
  clearSelection(event);
  document.getElementById(this.id).setAttribute("fill", "red");
  selected = this.id;
}

function clearSelection(event) {
  if (selected) {
    document.getElementById(selected).setAttribute("fill", "black");
    selected = null;
  }
}

function svgCursorPoint(event) {
  var svg   = document.getElementsByTagName('svg')[0];
  var pt = svg.createSVGPoint();
  pt.x = event.clientX;
  pt.y = event.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function movePoint(event) {

  // If there is no centroid/marker selected do nothing.
  if (!selected) {
    return;
  }

  // Get the position that was clicked.
  var pt = svgCursorPoint(event);

  // Update the centroid/marker circle position.
  var circle = document.getElementById(selected);
  circle.setAttribute("cx", pt.x);
  circle.setAttribute("cy", pt.y);

  // Find the tensor line associated with the centroid/marker.
  var words = selected.split("-");
  var type = words[0];
  var id = words[1];
  var tensor_id = "tensor-" + id
  var tensor = document.getElementById(tensor_id);
  if (type == "marker") {
    tensor.setAttribute("x1", pt.x);
    tensor.setAttribute("y1", pt.y);
  } else if (type == "centroid") {
    tensor.setAttribute("x2", pt.x);
    tensor.setAttribute("y2", pt.y);
  }
}

function deleteTensor(event) {
  var words = this.id.split("-");
  var type = words[0];
  var id = words[1];
  var marker_id = "marker-" + id
  var centroid_id = "centroid-" + id
  document.getElementById(this.id).setAttribute("visibility", "hidden");
  document.getElementById(marker_id).setAttribute("visibility", "hidden");
  document.getElementById(centroid_id).setAttribute("visibility", "hidden");
}


function init() {
  var markers = document.getElementsByClassName("marker");
  for (var i = 0; i < markers.length; i++) {
    markers[i].onmouseover = showElement;
    markers[i].onmouseout = hideElement;
    markers[i].onmousedown = selectElement;
  }
  var centroids = document.getElementsByClassName("centroid");
  for (var i = 0; i < centroids.length; i++) {
    centroids[i].onmouseover = showElement;
    centroids[i].onmouseout = hideElement;
    centroids[i].onmousedown = selectElement;
  }
  var tensors = document.getElementsByClassName("tensor");
  for (var i = 0; i < tensors.length; i++) {
    tensors[i].onmouseover = function(event) {document.getElementById(this.id).setAttribute("stroke", "red");};
    tensors[i].onmouseout = function(event) {document.getElementById(this.id).setAttribute("stroke", "black");};
    tensors[i].onmousedown = deleteTensor;
  }

  document.getElementById("segmentation").onmousedown = movePoint;

}