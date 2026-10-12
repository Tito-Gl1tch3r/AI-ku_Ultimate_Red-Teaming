from flask import Flask
from flask_socketio import SocketIO
from tkinter import Tk

# App Instance
app = Flask(__name__)
app.config['SECRET_KEY'] = 'shamballa'

# SocketIO Init
socketio = SocketIO(app)

# tkinter window for reading clipboard
win = Tk()
win.withdraw()

from . import views
from . import clipboard_thread
