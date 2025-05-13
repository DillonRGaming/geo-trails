from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import uuid
import os # Still needed for os.environ.get('PORT', ...)

app = Flask(__name__)
# HARDCODED SECRET KEY - Change this to your own random string if you want
# For personal use, this is simpler than environment variables.
# If this code is ever shared or made public, this key is exposed.
app.config['SECRET_KEY'] = 'this_is_my_personal_super_secret_key_for_geotrails_12345!' 
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*") # Keeping CORS open for personal use

active_users = {}
MAX_TRAIL_LENGTH = 30

print("Flask-SocketIO Server instance created and configured (hardcoded secret).")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = request.sid
    
    if user_id not in active_users:
        active_users[user_id] = {"lat": None, "lon": None, "trail": []}
    
    # print(f"Client connected: user_id (socket_id) = {user_id}")
    
    emit('user_connected_self', {'id': user_id, 'all_users': active_users})
    emit('all_users_update', active_users, broadcast=True, skip_sid=user_id)

@socketio.on('location_update')
def handle_location_update(data):
    user_id = request.sid

    if not user_id:
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
        emit('user_moved', update_data, broadcast=True, skip_sid=user_id) 
    # else:
        # print(f"Invalid location update for user {user_id} or user not in active_users: {data}")

@socketio.on('disconnect')
def handle_disconnect():
    user_id = request.sid
    
    if user_id in active_users:
        del active_users[user_id]
        emit('user_left', {'id': user_id}, broadcast=True)
        # print(f"Client {user_id} disconnected and removed.")
    # else:
        # print(f"Socket {user_id} disconnected, but user was not in active_users list.")

if __name__ == '__main__':
    # print("Attempting to start Flask-SocketIO server locally...")
    port = int(os.environ.get('PORT', 5000)) # Still keep this for Render/PaaS compatibility
    # print(f"Server will listen on host 0.0.0.0, port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, use_reloader=True)