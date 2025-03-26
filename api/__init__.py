from flask import Flask
from flask_cors import CORS


api = Flask(__name__)
CORS(api)

from .admin import admin_bp
api.register_blueprint(admin_bp, name='admin')
from .karyawan import karyawan_bp
api.register_blueprint(karyawan_bp, name='karyawan')
from .absensi import absensi_bp
api.register_blueprint(absensi_bp, name='absensi')