from datetime import timedelta
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from .admin import admin_bp
from .karyawan import karyawan_bp
from .absensi import absensi_bp
from .autentikasi import autentikasi_bp
from .cek_presensi import cek_presensi_bp


api = Flask(__name__)
CORS(api)

api.config['JWT_SECRET_KEY'] = 'berkahangsana2025'
api.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=60)
jwt = JWTManager(api)

api.register_blueprint(admin_bp, name='admin')
api.register_blueprint(karyawan_bp, name='karyawan')
api.register_blueprint(absensi_bp, name='absensi')
api.register_blueprint(autentikasi_bp, name='autentikasi')
api.register_blueprint(cek_presensi_bp, name='cek_presensi')