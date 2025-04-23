# Stream Cam System

A web-based streaming system that allows mobile phones to stream video and clients to view these streams.

## Features

- Stream video from any device with a camera (mobile phone, laptop, etc.)
- View multiple streams from a single interface
- Capture still images from any stream
- Automatic stream management (inactive streams are removed)
- Responsive design that works on all devices

## Requirements

- Python 3.6+
- Flask
- OpenCV
- NumPy
- Flask-SocketIO
- Eventlet

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Server

Run the Flask application:

```
python app.py
```

The server will start on `http://0.0.0.0:5000`

### For Streamers

1. Open `http://[server-ip]:5000/streamer` on your device
2. Allow camera access when prompted
3. Enter a name for your stream
4. Click "Start Streaming"

### For Viewers

1. Open `http://[server-ip]:5000/viewer` on your device
2. Select a stream from the list
3. Use the controls to capture images or view fullscreen

## Deployment on Ubuntu

To deploy this application on Ubuntu:

1. Install required packages:
   ```
   sudo apt update
   sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
   ```

2. Install virtual environment:
   ```
   sudo apt install python3-venv
   ```

3. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Run with Gunicorn (for production):
   ```
   pip install gunicorn
   gunicorn --worker-class eventlet -w 1 app:app -b 0.0.0.0:5000
   ```

## API Endpoints

- `/api/streams` - Get list of active streams
- `/api/register_stream` - Register a new stream
- `/api/upload_frame` - Upload a frame to a stream
- `/api/upload_base64_frame` - Upload a base64-encoded frame
- `/api/capture_image/<stream_id>` - Capture an image from a stream
- `/api/deactivate_stream/<stream_id>` - Deactivate a stream

## License

MIT License
