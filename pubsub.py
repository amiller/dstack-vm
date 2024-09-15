from flask import Flask, request, Response, stream_with_context, jsonify
import threading
import time
import json
from collections import deque
import queue

app = Flask(__name__)

# Configuration
DATA_EXPIRY_SECONDS = 60  # Time to keep data before removing
MAX_DATA_SIZE = 30 * 1024  # 30KB

# Thread-safe data storage
data_lock = threading.Lock()
data_queue = deque()

# Subscribers storage
subscribers_lock = threading.Lock()
subscribers = set()

def cleanup_data():
    """Background thread to clean up expired data."""
    while True:
        time.sleep(5)  # Cleanup interval
        current_time = time.time()
        with data_lock:
            while data_queue and (current_time - data_queue[0][0] > DATA_EXPIRY_SECONDS):
                data_queue.popleft()

def notify_subscribers(data):
    """Notify all subscribers with new data."""
    with subscribers_lock:
        for q in list(subscribers):
            try:
                q.put_nowait(data)
            except:
                subscribers.remove(q)

@app.route('/push', methods=['POST'])
def push_data():
    if not request.is_json:
        return jsonify({"error": "Invalid content type. JSON expected."}), 400

    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({"error": "Malformed JSON."}), 400

    # Serialize JSON to bytes to check size
    data_bytes = json.dumps(data).encode('utf-8')
    if len(data_bytes) > MAX_DATA_SIZE:
        return jsonify({"error": f"Data size exceeds {MAX_DATA_SIZE} bytes limit."}), 413

    timestamp = time.time()
    with data_lock:
        data_queue.append((timestamp, data))
    notify_subscribers(data)
    return jsonify({"status": "Data received."}), 200

def event_stream(q):
    """Generator function for SSE."""
    try:
        while True:
            data = q.get()
            # Serialize the data as JSON
            json_data = json.dumps({"data": data})
            yield f'{json_data}\n'
    except GeneratorExit:
        # Client disconnected
        with subscribers_lock:
            subscribers.remove(q)

@app.route('/subscribe', methods=['GET'])
def subscribe():
    q = queue.Queue()
    with subscribers_lock:
        subscribers.add(q)
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    return Response(stream_with_context(event_stream(q)), headers=headers)

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "message": "Welcome to the Pub/Sub server.",
        "endpoints": {
            "/push": "POST JSON data (max 30KB).",
            "/subscribe": "GET to subscribe to data stream via SSE."
        }
    }), 200

if __name__ == '__main__':
    # Start the cleanup thread
    cleanup_thread = threading.Thread(target=cleanup_data, daemon=True)
    cleanup_thread.start()
    # Run the Flask app
    app.run(host='127.0.0.1', port=5001, threaded=True)
