
from flask import Flask, render_template, request #flask--creates your web app,render_template--sends html file to browser ,request--gives info about incoming request
from flask_socketio import SocketIO, emit  #socketIO --enables webseckets,emit()--send data from backend--frontend
from dotenv import load_dotenv #load_dotenv is used to load the .env file
import requests #used to call external APIs(OPENROUTER AI)
import os#read the .env files

#setup
# Load environment variables
eventlet.monkey_patch()

load_dotenv()

app = Flask(__name__) #Creates Your webserver

socketio = SocketIO(
    app,
    cors_allowed_origins="*" #allow froentend to connect from any origin
)

# Store history per connected user
user_histories = {}


@app.route("/")
def home():
    return render_template("index.html")


def get_ai_response(history): #AI-Function

    try: #error handling

        api_key = os.getenv("OPENROUTER_API_KEY") #Reading api key

        if not api_key:
            return "OPENROUTER_API_KEY not found"

        response = requests.post(  #send Http request to OPENROUTER

            "https://openrouter.ai/api/v1/chat/completions", #AI endpoint

            headers={
                "Authorization": f"Bearer {api_key}", #api_key
                "Content-Type": "application/json" #sending json data 
            },

            json={
                "model": "openai/gpt-4o-mini",

                "messages": history
            }

        )

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        response.raise_for_status()  #if API fails -- throe error

        data = response.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:

        print("ERROR:", e)

        return f"Error: {e}"

#WEB SOCKET EVENT
@socketio.on("message") #Runs when frontend sends message
def handle_message(user_message): #function with parameter user_message

    socket_id = request.sid #each brpwser contain unique id-socket

    print("User:", user_message)

    # Create history if user is new
    if socket_id not in user_histories: #first time user -- create memory
        user_histories[socket_id] = [  #Control AI Behaviour

        {
            "role": "system",
            "content": """
You are a helpful AI chatbot.

You can answer:
- general knowledge questions
- movies
- coding
- explanations
- everyday questions

Do not refuse normal questions unless they are unsafe or harmful.
"""
        }

    ]

    # Store user message
    user_histories[socket_id].append(
        {
            "role": "user",
            "content": user_message
        }
    )

    # Send full history to model
    ai_response = get_ai_response(
        user_histories[socket_id]
    ) 

    print("AI RESPONSE:", ai_response)

    # Store assistant reply
    user_histories[socket_id].append(
        {
            "role": "assistant",
            "content": ai_response
        }
    )

    emit(
    "response",
    ai_response,
    to=socket_id
)


@socketio.on("disconnect")
def disconnect_user():

    socket_id = request.sid

    if socket_id in user_histories:

        del user_histories[socket_id]

        print(
            f"Deleted history for {socket_id}"
        )


if __name__ == "__main__":

    socketio.run(
        app,
        host="0.0.0.0",
        port=1000,
        debug=True
    )
