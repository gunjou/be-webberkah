import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restx import Api # type: ignore
from flask_cors import CORS

from .autentikasi import auth_ns
from .admin import admin_ns
from .pegawai import pegawai_ns
from .jenis_pegawai import jenis_pegawai_ns
from .tipe_pegawai import tipe_pegawai_ns
from .absensi import absensi_ns
from .rekapan import rekapan_ns
from .perhitungan_gaji import perhitungan_gaji_ns
from .izin_sakit import izin_ns
from .cuti import cuti_ns
from .lembur import lembur_ns
from .libur import libur_ns
from .leaderboard import leaderboard_ns
from .hutang import hutang_ns
# from .testdb import testdb_ns

from .utils.blacklist_store import is_blacklisted


api = Flask(__name__)
CORS(api)

# load .env
load_dotenv()

api.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY")
api.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=3)  # waktu login sesi
api.config['JWT_BLACKLIST_ENABLED'] = True
api.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']


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

authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'Masukkan token JWT Anda dengan format: **Bearer &lt;JWT&gt;**'
    }
}

# Swagger API instance
restx_api = Api(
        api, 
        version="2.0", 
        title="Berkah Angsana", 
        description="Dokumentasi API Berkah Angsana", 
        doc="/documentation",
        authorizations=authorizations,
        security='Bearer Auth'
    )

restx_api.add_namespace(auth_ns, path="/auth")
restx_api.add_namespace(admin_ns, path="/admin")
restx_api.add_namespace(pegawai_ns, path="/pegawai")
restx_api.add_namespace(jenis_pegawai_ns, path="/jenis-pegawai")
restx_api.add_namespace(tipe_pegawai_ns, path="/tipe-pegawai")
restx_api.add_namespace(absensi_ns, path="/absensi")
restx_api.add_namespace(rekapan_ns, path="/rekapan")
restx_api.add_namespace(perhitungan_gaji_ns, path="/perhitungan-gaji")
restx_api.add_namespace(izin_ns, path="/perizinan")
restx_api.add_namespace(cuti_ns, path="/cuti")
restx_api.add_namespace(lembur_ns, path="/lembur")
restx_api.add_namespace(libur_ns, path="/libur")
restx_api.add_namespace(leaderboard_ns, path="/peringkat")
restx_api.add_namespace(hutang_ns, path="/hutang")
# restx_api.add_namespace(testdb_ns, path="/test-db")