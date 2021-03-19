# Tiny flask app to keep a web server running so replit doesn't kill the process

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Web service is running."

def run():
  app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

