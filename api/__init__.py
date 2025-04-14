from datetime import timedelta
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from .admin import admin_bp
from .karyawan import karyawan_bp
from .absensi import absensi_bp
from .autentikasi import autentikasi_bp
from .cek_presensi import cek_presensi_bp
from .rekapan import rekapan_bp
from .perhitungan_gaji import perhitungan_gaji_bp
from .blacklist_store import is_blacklisted


api = Flask(__name__)
CORS(api)

api.config['JWT_SECRET_KEY'] = 'berkahangsana2025'
api.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)  # Atur sesuai kebutuhan
api.config['JWT_BLACKLIST_ENABLED'] = True
api.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']

api.register_blueprint(admin_bp, name='admin')
api.register_blueprint(karyawan_bp, name='karyawan')
api.register_blueprint(absensi_bp, name='absensi')
api.register_blueprint(autentikasi_bp, name='autentikasi')
api.register_blueprint(cek_presensi_bp, name='cek_presensi')
api.register_blueprint(perhitungan_gaji_bp, name='perhitungan_gaji')
api.register_blueprint(rekapan_bp, name='rekapan')


jwt = JWTManager(api)

@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    return is_blacklisted(jwt_payload['jti'])


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {'status': 'Token expired, Login ulang'}, 401

@jwt.invalid_token_loader
def invalid_token_callback(reason):
    print("ALASAN TOKEN INVALID:", reason) 
    return {'status': 'Invalid token'}, 401

@jwt.unauthorized_loader
def missing_token_callback(reason):
    return {'status': 'Missing token'}, 401