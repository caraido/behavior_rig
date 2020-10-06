# this demo serves a react app that streams white noise data encoded in jpeg

# in practice we will want to stream hevc data, which requires a different approach due to interframe compression
# we can do this using the libde265.js javascript decoder, modified for websockets (https://github.com/strukturag/libde265.js/pull/10/files/4d29e7bf3a1de850b8c3810610d16bd14698de0d)
# frames will be transmitted by flask in chunks via a websocket and attached to a canvas in js

from flask import Response, Flask, render_template, request
from numpy import random
from cv2 import imencode


def random_data():
  while True:
    # encode the data using jpg format
    (flag, encoded_image) = imencode('.jpg', 256*random.rand(300, 200))
    if not flag:
      continue

    # convert to a bytearray for serving
    yield(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + bytes(encoded_image) + b'\r\n')


# create the server
app = Flask(__name__)


# define the index route
@app.route('/')
def index():
  return render_template('index.html', flask_token="Hello world")


# individual cameras will be available at /cameraN
@app.route('/camera<int:camera_id>')
def show_data(camera_id):
  return Response(random_data(), mimetype='multipart/x-mixed-replace; boundary=frame')


# allow user to interact with the recording through a simple API
@app.route('/api/', methods=['POST'])
def start_recording():
  print(request.json['test'])
  # lets the browser know that we received its request
  return Response(status=200)


# host the server on the local machine
if __name__ == '__main__':
  app.run(host='127.0.0.1', port='3001', debug=True, use_reloader=False)