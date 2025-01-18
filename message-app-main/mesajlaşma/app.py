from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# MongoDB bağlantısı
client = MongoClient('mongodb://localhost:27017/')
db = client['chat_app']

# Kullanıcı Kaydı
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if db.users.find_one({"username": username}):
        return jsonify({"message": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    db.users.insert_one({"username": username, "password": hashed_password})
    return jsonify({"message": "User registered successfully"}), 201

# Kullanıcı Girişi
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.users.find_one({"username": username})
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"message": "Invalid username or password"}), 401

    return jsonify({"message": "Login successful", "username": username}), 200

# Kullanıcı Listesi
@app.route('/users', methods=['GET'])
def get_users():
    users = list(db.users.find({}, {"_id": 0, "password": 0}))
    return jsonify(users), 200

# Kullanıcıdan Alınan ve Gönderilen Mesajlar
@app.route('/messages', methods=['POST'])
def get_messages():
    data = request.json
    current_user = data.get('current_user')
    target_user = data.get('target_user')

    messages = list(db.messages.find({
        "$or": [
            {"sender": current_user, "receiver": target_user},
            {"sender": target_user, "receiver": current_user}
        ]
    }, {"_id": 0}))

    return jsonify(messages), 200

# Mesajları Sil
@app.route('/delete_messages', methods=['POST'])
def delete_messages():
    data = request.json
    current_user = data.get('current_user')
    target_user = data.get('target_user')

    # İki kullanıcı arasındaki tüm mesajları sil
    db.messages.delete_many({
        "$or": [
            {"sender": current_user, "receiver": target_user},
            {"sender": target_user, "receiver": current_user}
        ]
    })
    return jsonify({"message": "Messages deleted successfully"}), 200

# Mesaj Gönderimi
@socketio.on('send_message')
def handle_send_message(data):
    sender = data.get('sender')
    receiver = data.get('receiver')
    message = data.get('message')

    # Mesajı veritabanına kaydet
    db.messages.insert_one({"sender": sender, "receiver": receiver, "message": message})

    # Mesajı alıcıya gönder
    emit('receive_message', data, room=receiver)

# Kullanıcı Sohbet Odasına Katılım
@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    join_room(username)
    print(f"User {username} joined their private room.")

if __name__ == "__main__":
    socketio.run(app, debug=True)