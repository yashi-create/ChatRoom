from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random 
from string import ascii_uppercase

app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjdsnjs"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

@app.route("/", methods=["POST", "GET"])  #allowed methods. 1st route to our website to homepage
def home():
    session.clear()    #we don't want the user to directly use / to join a room, so with this the user have to visit the home page to join a chatroom
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)
        
        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code

        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name       #look for sessions wrt socket.io
        return redirect(url_for("room"))     #function we are redirecting to

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:       #either we join a room or we are creatring a new room
        return redirect(url_for("home"))
    return render_template("room.html", code=room, messages=rooms[room]["messages"])


#message goes to server and then everyone receives it
@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}") 


#we look for the users name and room code to decide in which room to put them in
#we need to connect the rooms we have created and the rooms in socketio
@socketio.on("connect")
def connect(auth):            
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:                      #user joining a room that doesn't exist
        leave_room(room)
        return

    join_room(room)                           #passing the room code to join the room
    send({"name": name, "message": "has entered the room"}, to=room)                       #message to all the people in socket room
    rooms[room]["members"] += 1                                       #keeping a track of how many people are in the room, they have finally connected to the socket room 
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:            #everyone leaves we delete the room
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

#with the above code when a user refreshes the page and if he is the only user in the room, the count of members goes to 0 and the room is deleted
#this is not the case with more than 1 user

if __name__ == "__main__":
    socketio.run(app, debug=True)