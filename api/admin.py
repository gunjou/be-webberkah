from flask import Blueprint, request

from .query import get_list_admin, add_admin


admin_bp = Blueprint('api', __name__)

@admin_bp.route('/api/admin', methods=['GET', 'POST'])
def admin():
    if  request.method == 'GET':
        list_admin = get_list_admin().fetchall()
        result = [{
            'id_admin': row[0],
            'nama': row[1],
            'username': row[2],
            'password': row[3]
            # 'created_at': row[4],
            # 'updated_at': row[5]
            } for row in list_admin]
        return result
    
    elif  request.method == 'POST':
        nama = request.json.get("nama", None).title()
        username = request.json.get("username", None)
        password = request.json.get("password", None)

        if not nama or not username or not password:
            return {'status': "field can't blank"}, 403
        else:
            try:
                add_admin(nama, username, password)
                return {'status': "Success add data"}, 200
            except:
                return {'status': "Add data failed"}, 403

