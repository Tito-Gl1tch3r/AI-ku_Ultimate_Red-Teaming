'''
This thread runs in background checking for changes in clipboard content every
second and if change found, emits an SocketIO event to client.
'''

import threading
import time
import os
import ntpath
from shutil import copyfile
from . import win
from . import socketio

def clipboardCheck():
    # get the clipboard content
    cb = win.clipboard_get()

    # check clipboard every second
    while(True):
        time.sleep(1)

        # if clipboard content has changed
        if cb != win.clipboard_get():
            cb = win.clipboard_get()

            # if the content is a path
            if os.path.exists(cb):
                '''
                If the content is a path to an image, move the image to temp &
                emit the new path.
                '''
                # check the extension for image
                _, file_ext = os.path.splitext(cb)
                if file_ext in ['.png', '.jpg', '.jpeg']:
                    location = 'static/temp/{}'.format(ntpath.basename(cb))
                    copyfile(cb, './clipSync/{}'.format(location)) # copy image to temp
                    socketio.emit('image', location) # emit new path
                else:
                    socketio.emit('message', cb)
            else:
                socketio.emit('message', cb)

# Thread Init
thread = threading.Thread(target=clipboardCheck)
thread.start()
