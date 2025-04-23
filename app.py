from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
import threading
import time
import os
import base64
from datetime import datetime

app = Flask(__name__)

# Dictionary to store active streams
streams = {}
# Lock for thread-safe operations on the streams dictionary
streams_lock = threading.Lock()


class Stream:
    def __init__(self, stream_id, name):
        self.stream_id = stream_id
        self.name = name
        self.frame = None
        self.last_update = time.time()
        self.active = True
        self.clients = 0
        self.quality_info = {"resolution": "1280x720", "fps": 10, "quality": 70}

    def update_frame(self, frame):
        self.frame = frame
        self.last_update = time.time()

    def get_frame(self):
        return self.frame

    def is_active(self):
        # Consider a stream inactive if no updates for 30 seconds
        return self.active and (time.time() - self.last_update) < 30


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/streamer")
def streamer():
    return render_template("streamer.html")


@app.route("/viewer")
def viewer():
    return render_template("viewer.html")


@app.route("/api/streams", methods=["GET"])
def get_streams():
    with streams_lock:
        active_streams = {
            id: {
                "name": stream.name,
                "active": stream.is_active(),
                "last_update": stream.last_update,
                "clients": stream.clients,
                "quality_info": stream.quality_info,
            }
            for id, stream in streams.items()
            if stream.is_active()
        }
    return jsonify(active_streams)


@app.route("/api/register_stream", methods=["POST"])
def register_stream():
    data = request.json
    stream_id = data.get("stream_id", str(time.time()))
    name = data.get("name", f"Stream {stream_id}")

    # Get initial quality settings if provided
    quality_info = data.get("quality_info", {})

    with streams_lock:
        if stream_id not in streams:
            streams[stream_id] = Stream(stream_id, name)
            print(f"New stream registered: {name} (ID: {stream_id})")

            # Set initial quality settings if provided
            if quality_info:
                streams[stream_id].quality_info.update(quality_info)
        else:
            streams[stream_id].active = True
            print(f"Stream reactivated: {name} (ID: {stream_id})")

            # Update quality settings if provided
            if quality_info:
                streams[stream_id].quality_info.update(quality_info)

    return jsonify({"status": "success", "stream_id": stream_id})


@app.route("/api/upload_frame", methods=["POST"])
def upload_frame():
    stream_id = request.form.get("stream_id")
    if not stream_id or stream_id not in streams:
        return jsonify({"status": "error", "message": "Invalid stream ID"})

    if "frame" not in request.files:
        return jsonify({"status": "error", "message": "No frame provided"})

    file = request.files["frame"]
    npimg = np.fromfile(file, np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

    with streams_lock:
        if stream_id in streams:
            streams[stream_id].update_frame(frame)

    return jsonify({"status": "success"})


@app.route("/api/upload_base64_frame", methods=["POST"])
def upload_base64_frame():
    data = request.json
    stream_id = data.get("stream_id")
    base64_frame = data.get("frame")

    # Get quality settings if provided
    quality_info = data.get("quality_info", {})

    if not stream_id or stream_id not in streams:
        return jsonify({"status": "error", "message": "Invalid stream ID"})

    if not base64_frame:
        return jsonify({"status": "error", "message": "No frame provided"})

    try:
        # Decode base64 image
        base64_data = base64_frame.split(",")[1] if "," in base64_frame else base64_frame
        img_data = base64.b64decode(base64_data)
        npimg = np.frombuffer(img_data, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        with streams_lock:
            if stream_id in streams:
                streams[stream_id].update_frame(frame)

                # Update quality info if provided
                if quality_info:
                    streams[stream_id].quality_info.update(quality_info)

        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route("/api/capture_image/<stream_id>", methods=["GET"])
def capture_image(stream_id):
    if stream_id not in streams:
        return jsonify({"status": "error", "message": "Stream not found"})

    stream = streams[stream_id]
    frame = stream.get_frame()

    if frame is None:
        return jsonify({"status": "error", "message": "No frame available"})

    # Create directory for captures if it doesn't exist
    if not os.path.exists("captures"):
        os.makedirs("captures")

    # Save the image with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"captures/capture_{stream_id}_{timestamp}.jpg"
    cv2.imwrite(filename, frame)

    # Convert to base64 for response
    _, buffer = cv2.imencode(".jpg", frame)
    jpg_as_text = base64.b64encode(buffer).decode("utf-8")

    return jsonify({"status": "success", "image": f"data:image/jpeg;base64,{jpg_as_text}", "saved_as": filename})


def generate_frames(stream_id):
    with streams_lock:
        if stream_id not in streams:
            return
        streams[stream_id].clients += 1

    try:
        while True:
            with streams_lock:
                if stream_id not in streams or not streams[stream_id].is_active():
                    break

                frame = streams[stream_id].get_frame()

            if frame is None:
                time.sleep(0.1)
                continue

            # Encode the frame as JPEG
            _, buffer = cv2.imencode(".jpg", frame)
            frame_bytes = buffer.tobytes()

            # Yield the frame in the format expected by multipart/x-mixed-replace
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

            time.sleep(0.033)  # ~30 FPS
    finally:
        with streams_lock:
            if stream_id in streams:
                streams[stream_id].clients -= 1


@app.route("/stream/<stream_id>")
def stream(stream_id):
    return Response(generate_frames(stream_id), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/deactivate_stream/<stream_id>", methods=["POST"])
def deactivate_stream(stream_id):
    with streams_lock:
        if stream_id in streams:
            streams[stream_id].active = False
            print(f"Stream deactivated: {streams[stream_id].name} (ID: {stream_id})")
            return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Stream not found"})


# Cleanup inactive streams periodically
def cleanup_streams():
    while True:
        time.sleep(60)  # Check every minute
        with streams_lock:
            for stream_id in list(streams.keys()):
                if not streams[stream_id].is_active():
                    print(f"Removing inactive stream: {streams[stream_id].name} (ID: {stream_id})")
                    del streams[stream_id]


# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_streams, daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    # Create captures directory if it doesn't exist
    if not os.path.exists("captures"):
        os.makedirs("captures")

    # Run the Flask app
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=True)
