from flask import Blueprint, request
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import jwt_required


from .query import get_list_admin, add_admin


admin_bp = Blueprint('api', __name__)

@admin_bp.route('/admin', methods=['GET'])
@jwt_required()
def admin():
    # Mengambil daftar admin
    list_admin = get_list_admin()  # Menggunakan fungsi yang sudah dioptimalkan
    return {'admin': list_admin}, 200  # Mengembalikan hasil dalam format JSON

@admin_bp.route('/admin', methods=['POST'])
@jwt_required()
def tambah_admin():
        nama = request.json.get("nama", None).title()
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        if not all([nama, username, password]):
            return {'status': "All fields are required"}, 400  # Menggunakan 400 untuk Bad Request

        try:
            admin_id = add_admin(nama, username, password)  # Menyimpan ID admin yang baru ditambahkan
            if admin_id is None:
                return {'status': "Add data failed"}, 500  # Menggunakan 500 untuk Internal Server Error
            return {'status': "Success add data", 'id_admin': admin_id}, 201  # Menggunakan 201 untuk Created
        except SQLAlchemyError as e:
            return {'status': f"Add data failed: {str(e)}"}, 500  # Mengembalikan pesan kesalahan
