from flask import Flask, request, jsonify
import requests
from controller.maps_controller import maps_controller
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

app.register_blueprint(maps_controller)
if __name__ == '__main__':
    app.run(debug=False)
