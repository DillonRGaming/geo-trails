from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a_very_secure_default_secret_key_123!')
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

active_users = {}  # Stores {user_id: {"lat": float, "lon": float, "trail": list}}
# No need for socket_to_user anymore, as user_id will BE the request.sid

MAX_TRAIL_LENGTH = 30 # Increased trail length slightly

print("Flask-SocketIO Server instance created and configured.")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = request.sid # Use the socket's unique session ID as the user_id
    
    if user_id not in active_users:
        active_users[user_id] = {"lat": None, "lon": None, "trail": []}
    
    print(f"Client connected: user_id (socket_id) = {user_id}")
    
    # Send this new user their ID and the current state of all other users
    emit('user_connected_self', {'id': user_id, 'all_users': active_users})
    
    # Notify all *other* clients that a new user has connected (they will update their maps)
    # We send the complete active_users list so they can add the new one
    emit('all_users_update', active_users, broadcast=True, skip_sid=user_id)

@socketio.on('location_update')
def handle_location_update(data):
    user_id = request.sid # Identify user by their socket ID

    if not user_id: # Should not happen if client is connected
        print(f"Location update from unknown socket data: {data}")
        return

    lat = data.get('lat')
    lon = data.get('lon')

    if user_id in active_users and lat is not None and lon is not None:
        active_users[user_id]['lat'] = lat
        active_users[user_id]['lon'] = lon
        
        active_users[user_id]['trail'].append({'lat': lat, 'lon': lon})
        if len(active_users[user_id]['trail']) > MAX_TRAIL_LENGTH:
            active_users[user_id]['trail'].pop(0)

        update_data = {'id': user_id, 'lat': lat, 'lon': lon, 'trail': active_users[user_id]['trail']}
        # Broadcast to everyone EXCEPT the sender
        emit('user_moved', update_data, broadcast=True, skip_sid=user_id) 
    else:
        print(f"Invalid location update for user {user_id} or user not in active_users: {data}")

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid # Identify user by their socket ID
    
    if user_id in active_users:
        del active_users[user_id]
        emit('user_left', {'id': user_id}, broadcast=True)
        print(f"Client {user_id} disconnected and removed.")
    else:
        print(f"Socket {user_id} disconnected, but user was not in active_users list.")

if __name__ == '__main__':
    print("Attempting to start Flask-SocketIO server locally...")
    port = int(os.environ.get('PORT', 5000))
    print(f"Server will listen on host 0.0.0.0, port {port}")
    # For local development, use_reloader can be True, but for Gunicorn/production it's often not needed or problematic.
    # debug=True should also be False in production.
    socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=True)