var selected = null;

function toggleChannels() {
  var wall_intensity = document.getElementById("cell_wall_intensity");
  var marker_intensity = document.getElementById("marker_intensity");
  if (wall_intensity.getAttribute("visibility") == "visible") {
    wall_intensity.setAttribute("visibility", "hidden");
    marker_intensity.setAttribute("visibility", "visible");
  }
  else {
    wall_intensity.setAttribute("visibility", "visible");
    marker_intensity.setAttribute("visibility", "hidden");
  }
}

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

function clearSelection(event) {
  if (selected) {
    document.getElementById(selected).setAttribute("fill", "black");
    selected = null;
  }
}

function action_from_json(info) {
  var tensor_id = "tensor-" + info["tensor_id"];
  var marker_id = "marker-" + info["tensor_id"];
  var centroid_id = "centroid-" + info["tensor_id"];

  var tensor = document.getElementById(tensor_id);
  var marker = document.getElementById(marker_id);
  var centroid = document.getElementById(centroid_id);

  if (info["action"] == "update") {
    for (var key in info) {
      var value = info[key];
      if (key == "tensor_id" || key == "update") {
        continue;
      }
      else {
        if (key == "active") {
          if (value) {
            tensor.setAttribute("visibility", "visible");
            marker.setAttribute("visibility", "visible");
            centroid.setAttribute("visibility", "visible");
          }
          else {
            tensor.setAttribute("visibility", "hidden");
            marker.setAttribute("visibility", "hidden");
            centroid.setAttribute("visibility", "hidden");
          }
        }
        else {
          var x = value[1];
          var y = value[0];
          if (key == "marker") {
            // Update the tensor line.
            tensor.setAttribute("x1", x);
            tensor.setAttribute("y1", y);

            // Update the marker circle.
            marker.setAttribute("cx", x);
            marker.setAttribute("cy", y);
          }
          if (key == "centroid") {
            tensor.setAttribute("x2", x);
            tensor.setAttribute("y2", y);

            // Update the centroid circle.
            centroid.setAttribute("cx", x);
            centroid.setAttribute("cy", y);
          }
        }
      }
    }
  }
}

function undo(event) {
  // Ajax call.
  var xhttp = new XMLHttpRequest();
  var url = "undo"
  xhttp.onreadystatechange = function() {
    if (xhttp.readyState == 4 && xhttp.status == 200) {
      if (!xhttp.responseText.startsWith("None")) {
        var info = JSON.parse(xhttp.responseText);
        action_from_json(info);
      }
    }
  };
  xhttp.open("POST", url, true);
  xhttp.send()
}

function redo(event) {
  // Ajax call.
  var xhttp = new XMLHttpRequest();
  var url = "redo"
  xhttp.onreadystatechange = function() {
    if (xhttp.readyState == 4 && xhttp.status == 200) {
      if (!xhttp.responseText.startsWith("None")) {
        var info = JSON.parse(xhttp.responseText);
        action_from_json(info);
      }
    }
  };
  xhttp.open("POST", url, true);
  xhttp.send()
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

function svgCursorPoint(event) {
  var svg   = document.getElementsByTagName('svg')[0];
  var pt = svg.createSVGPoint();
  pt.x = event.clientX;
  pt.y = event.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function updateMarker(id, y, x) {
  var tensor_id = "tensor-" + id
  var tensor = document.getElementById(tensor_id);
  tensor.setAttribute("x1", x);
  tensor.setAttribute("y1", y);

  // Ajax call.
  var xhttp = new XMLHttpRequest();
  var url = "update_marker/" + id + "/" + y.toFixed(4) + "/" + x.toFixed(4)
  xhttp.open("POST", url, true);
  xhttp.send()
}

function updateCentroid(id, y, x) {
  var tensor_id = "tensor-" + id
  var tensor = document.getElementById(tensor_id);
  tensor.setAttribute("x2", x);
  tensor.setAttribute("y2", y);

  // Ajax call.
  var xhttp = new XMLHttpRequest();
  var url = "update_centroid/" + id + "/" + y.toFixed(4) + "/" + x.toFixed(4)
  xhttp.open("POST", url, true);
  xhttp.send()
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
  if (type == "marker") {
    updateMarker(id, pt.y, pt.x);
  } else if (type == "centroid") {
    updateCentroid(id, pt.y, pt.x);
  }
}

function inactivateTensor(event) {
  var words = this.id.split("-");
  var type = words[0];
  var id = words[1];
  var marker_id = "marker-" + id
  var centroid_id = "centroid-" + id
  document.getElementById(this.id).setAttribute("visibility", "hidden");
  document.getElementById(marker_id).setAttribute("visibility", "hidden");
  document.getElementById(centroid_id).setAttribute("visibility", "hidden");

  // Ajax call.
  var xhttp = new XMLHttpRequest();
  xhttp.open("POST", "inactivate_tensor/" + id, true);
  xhttp.send()
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
    tensors[i].onmousedown = inactivateTensor;
  }

  document.getElementById("segmentation").onmousedown = movePoint;

}
