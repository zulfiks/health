from flask import Flask, jsonify, request
from flask_cors import CORS
from extensions import db 
from models import Laporan, Admin, Konten, Pengguna, RiwayatAktivitas, RiwayatMakan, Makanan, RiwayatLari
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)

# ==========================================
# 1. KONFIGURASI DATABASE & JWT
# ==========================================
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@127.0.0.1:3306/healthify"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299  
app.config["SQLALCHEMY_POOL_PRE_PING"] = True 

app.config['SECRET_KEY'] = 'kunci-rahasia-healthify-jangan-disebar-999'
app.config["JWT_SECRET_KEY"] = "super-secret-jwt-key-ubah-nanti" 
jwt = JWTManager(app)

# ==========================================
# 2. KONFIGURASI CORS
# ==========================================
CORS(app, resources={r"/api/*": {"origins": "*"}})

db.init_app(app) 

with app.app_context():
    db.create_all()
    print("[INFO] Database & Tabel Siap!")

# ==========================================
# 3. API ADMIN
# ==========================================

@app.route('/api/login/admin', methods=['POST'])
def login_admin():
    data = request.get_json()
    email_admin = data.get('email')
    password_admin = data.get('password') 
    
    admin = Admin.query.filter_by(email=email_admin).first()

    # Catatan: Disarankan menggunakan check_password_hash di masa depan
    if admin and str(admin.password_hash) == str(password_admin):
        access_token = create_access_token(identity=admin.email)
        return jsonify({
            "status": "success", 
            "message": "Login Admin Berhasil!", 
            "access_token": access_token,
            "user": admin.to_dict()
        }), 200
    return jsonify({"message": "Email atau Password Admin Salah"}), 401

@app.route('/api/admin/profile', methods=['GET'])
@jwt_required()
def get_admin_profile():
    try:
        current_email = get_jwt_identity()
        admin = Admin.query.filter_by(email=current_email).first()
        if not admin:
            return jsonify({"message": "Admin tidak ditemukan"}), 404
        return jsonify(admin.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/profile', methods=['PUT'])
@jwt_required()
def update_admin_profile():
    try:
        current_email = get_jwt_identity()
        admin = Admin.query.filter_by(email=current_email).first()
        if not admin:
            return jsonify({"message": "Akun admin tidak ditemukan"}), 404

        data = request.get_json()
        if 'nama' in data: admin.nama = data['nama']

        password_baru = data.get('password_baru')
        password_lama = data.get('password_lama')

        if password_baru:
            if str(admin.password_hash) != str(password_lama):
                return jsonify({"message": "Gagal: Password lama salah!"}), 401
            admin.password_hash = password_baru

        db.session.commit()
        return jsonify({"message": "Profil berhasil diperbarui", "user": admin.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

        # Tambahkan di bagian update_user atau buat route baru

@app.route('/api/users/<int:id>/assessment', methods=['PUT'])
def save_assessment(id):
    try:
        user = Pengguna.query.get_or_404(id)
        data = request.get_json()
        ans = data.get('answers', {})

        # 1. Simpan Jawaban Mentah ke Database
        user.pola_makan = ans.get('pola_makan')
        user.aktivitas_fisik = ans.get('aktivitas')
        user.ngemil = ans.get('ngemil')
        user.konsumsi_gula = ans.get('gula')
        # ... simpan kolom lainnya ...

        # 2. Logika Perhitungan Skor (Contoh)
        score = 0
        if ans.get('pola_makan') == "Sering telat": score += 10
        if ans.get('aktivitas') == "Jarang": score += 20
        # ... tambahkan logika bobot nilai lainnya ...

        # 3. Tentukan Level & Target
        user.risk_score = score
        if score >= 50:
            user.risk_level = "Tinggi"
            user.health_target = "Turunkan 3-5kg dalam 4 minggu dengan diet defisit kalori."
        else:
            user.risk_level = "Rendah"
            user.health_target = "Pertahankan pola makan dan olahraga 3x seminggu."

        db.session.commit()
        return jsonify({"message": "Analisis disimpan!", "data": user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- ENDPOINT BARU: Simpan Hasil Analisis Risiko ---
@app.route('/api/users/<int:id>/assessment', methods=['PUT'])
def update_assessment(id):
    try:
        user = Pengguna.query.get_or_404(id)
        data = request.get_json()
        ans = data.get('answers', {})

        # 1. Simpan Jawaban Pilihan User ke Database
        user.pola_makan = str(ans.get('pola_makan'))
        user.aktivitas_fisik = str(ans.get('aktivitas'))
        user.ngemil = str(ans.get('ngemil'))
        user.konsumsi_gula = str(ans.get('gula'))
        # ... tambahkan kolom lain jika ada ...

        # 2. Logika Perhitungan Skor Sederhana (Contoh)
        total_score = sum(int(v) for v in ans.values())
        
        # 3. Tentukan Level & Target Berdasarkan Skor
        if total_score >= 30:
            level = "Tinggi"
            target = "Fokus pada diet defisit kalori dan olahraga intens 4-5x seminggu."
        elif total_score >= 15:
            level = "Sedang"
            target = "Mulai kurangi camilan manis dan jalan kaki 10.000 langkah sehari."
        else:
            level = "Rendah"
            target = "Pertahankan pola makan sehat dan aktivitas fisik rutin."

        # 4. Update Hasil Analisis ke Database
        user.risk_score = total_score
        user.risk_level = level
        user.health_target = target
        
        db.session.commit()

        return jsonify({
            "message": "Analisis Berhasil Disimpan!",
            "score": total_score,
            "level": level,
            "target": target
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error Assessment: {str(e)}")
        return jsonify({"message": "Gagal menyimpan analisis", "error": str(e)}), 500
# ==========================================
# 4. API MAKANAN
# ==========================================

@app.route('/api/makanan/search', methods=['GET'])
def search_makanan():
    try:
        query_param = request.args.get('q', '').strip()
        if not query_param: return jsonify([]), 200
        hasil_cari = Makanan.query.filter(Makanan.name.ilike(f"%{query_param}%")).limit(50).all()
        return jsonify([item.to_dict() for item in hasil_cari]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/makanan', methods=['GET', 'POST'])
def handle_makanan():
    if request.method == 'GET':
        try:
            semua_makanan = Makanan.query.all()
            return jsonify([item.to_dict() for item in semua_makanan]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_food = Makanan(
                name=data['name'], calories=float(data['calories']),
                proteins=float(data['proteins']), fat=float(data['fat']),
                carbohydrate=float(data['carbohydrate']), image=data['image']
            )
            db.session.add(new_food)
            db.session.commit()
            return jsonify({"message": "Berhasil ditambahkan", "data": new_food.to_dict()}), 201
        except Exception as e:
            db.session.rollback() 
            return jsonify({"error": str(e)}), 500

@app.route('/api/makanan/<int:id>', methods=['PUT', 'DELETE'])
def handle_single_makanan(id):
    food = Makanan.query.get_or_404(id)
    if request.method == 'PUT':
        try:
            data = request.get_json()
            food.name = data['name']
            food.calories = float(data['calories'])
            food.proteins = float(data['proteins'])
            food.fat = float(data['fat'])
            food.carbohydrate = float(data['carbohydrate'])
            food.image = data['image']
            db.session.commit()
            return jsonify({"message": "Makanan diperbarui"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
            
    if request.method == 'DELETE':
        try:
            db.session.delete(food)
            db.session.commit()
            return jsonify({"message": "Makanan dihapus"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

# ==========================================
# 5. API RIWAYAT & SUMMARY
# ==========================================

@app.route('/api/riwayat/makan', methods=['POST'])
def add_riwayat_makan():
    try:
        data = request.get_json()
        new_riwayat = RiwayatMakan(
            user_id=data['user_id'], nama_makanan=data['nama_makanan'],
            kalori=int(data['kalori']), protein=float(data['proteins']),   
            lemak=float(data['fat']), karbo=float(data['carbohydrate']), 
            waktu_makan=data['waktu'], tanggal=datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(new_riwayat)
        user = Pengguna.query.get(data['user_id'])
        if user: user.poin += 5 
        db.session.commit()
        return jsonify({"message": "Berhasil! +5 Poin.", "total_poin": user.poin}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/summary/<int:user_id>', methods=['GET'])
def get_daily_summary(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    user = Pengguna.query.get_or_404(user_id)
    
    target_kalori = 2000 
    if user.berat > 0 and user.tinggi > 0:
        if user.gender == 'L' or user.gender == 'Laki-Laki':
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) + 5
        else:
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) - 161
        target_kalori = int(target_kalori * 1.2) 
    
    riwayat = RiwayatMakan.query.filter_by(user_id=user_id, tanggal=today).all()
    total_kalori = sum(r.kalori for r in riwayat)
    
    return jsonify({
        "total_kalori": total_kalori,
        "target_kalori": target_kalori,
        "pagi": [r.to_dict() for r in riwayat if r.waktu_makan == 'Pagi'],
        "siang": [r.to_dict() for r in riwayat if r.waktu_makan == 'Siang'],
        "malam": [r.to_dict() for r in riwayat if r.waktu_makan == 'Malam']
    }), 200

# ==========================================
# 6. API USERS (REGISTRASI, LOGIN, & PROFILE)
# ==========================================

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if Pengguna.query.filter_by(email=data['email']).first():
        return jsonify({"message": "Email sudah terdaftar!"}), 400

    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = Pengguna(
        nama=data['nama'], email=data['email'], password=hashed_password, 
        umur=0, gender='-', tinggi=0, berat=0, poin=0
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registrasi Berhasil!", "user": new_user.to_dict()}), 201

@app.route('/api/login/user', methods=['POST'])
def login_user():
    data = request.get_json()
    user = Pengguna.query.filter_by(email=data.get('email')).first()

    if not user: return jsonify({"message": "Email tidak ditemukan"}), 401

    if check_password_hash(user.password, data.get('password')):
        return jsonify({"status": "success", "message": "Login Berhasil!", "user": user.to_dict()}), 200
    return jsonify({"message": "Password Salah"}), 401

@app.route('/api/users', methods=['GET'])
def get_all_users():
    try:
        users = Pengguna.query.all()
        return jsonify([u.to_dict() for u in users]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:id>', methods=['GET'])
def get_single_user(id):
    try:
        user = Pengguna.query.get_or_404(id)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    try:
        user = Pengguna.query.get_or_404(id)
        data = request.form if request.files else request.get_json()

        # Update Data Dasar
        if 'nama' in data: user.nama = data['nama']
        if 'email' in data: user.email = data['email']
        if 'umur' in data: user.umur = int(float(data['umur']))
        if 'tinggi' in data: user.tinggi = float(data['tinggi'])
        if 'berat' in data: user.berat = float(data['berat'])

        # Logika Ganti Password (Jika ada input password baru)
        password_baru = data.get('password')
        password_lama = data.get('old_password')
        if password_baru and password_lama:
            if not check_password_hash(user.password, password_lama):
                return jsonify({"message": "Gagal: Password lama salah!"}), 401
            user.password = generate_password_hash(password_baru, method='pbkdf2:sha256')

        # Logika Upload Foto
        if 'foto' in request.files:
            file = request.files['foto']
            filename = f"user_{id}_{int(datetime.now().timestamp())}.jpg"
            upload_path = os.path.join(app.root_path, 'static/uploads', filename)
            file.save(upload_path)
            user.foto = filename 

        db.session.commit()
        
        # Kembalikan data murni (Tanpa IP Hardcoded)[cite: 13, 15]
        return jsonify({"message": "Update Berhasil!", "user": user.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Gagal update", "error": str(e)}), 500

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    try:
        user = Pengguna.query.get(id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "Akun dihapus"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ==========================================
# 7. API LAPORAN & KONTEN
# ==========================================

@app.route('/api/laporan', methods=['GET', 'POST'])
def handle_laporan():
    if request.method == 'GET':
        try:
            reports = Laporan.query.all()
            return jsonify([r.to_dict() for r in reports]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    # Tambahkan metode POST jika dibutuhkan untuk aplikasi di sini

@app.route('/api/laporan/<int:id>/status', methods=['PUT'])
def update_status_laporan(id):
    try:
        data = request.get_json()
        laporan = Laporan.query.get_or_404(id)
        laporan.status = data.get('status')
        db.session.commit()
        return jsonify({"message": f"Status laporan #{id} diperbarui"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/laporan/<int:id>', methods=['DELETE'])
def delete_laporan(id):
    try:
        laporan = Laporan.query.get_or_404(id)
        db.session.delete(laporan)
        db.session.commit()
        return jsonify({"message": "Laporan dihapus"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/konten', methods=['GET', 'POST'])
def handle_konten():
    if request.method == 'GET':
        try:
            data = Konten.query.all()
            return jsonify([item.to_dict() for item in data]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_konten = Konten(
                judul=data['judul'], kategori=data['kategori'],
                publikasi=data['publikasi'], tautan=data['tautan'], foto=data.get('foto')
            )
            db.session.add(new_konten)
            db.session.commit()
            return jsonify({"message": "Konten berhasil ditambah"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

@app.route('/api/konten/<int:id>', methods=['PUT', 'DELETE'])
def handle_single_konten(id):
    konten = Konten.query.get_or_404(id)
    if request.method == 'PUT':
        try:
            data = request.get_json()
            konten.judul = data['judul']
            konten.kategori = data['kategori']
            konten.publikasi = data['publikasi']
            konten.tautan = data['tautan']
            konten.foto = data.get('foto')
            db.session.commit()
            return jsonify({"message": "Konten diperbarui"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500
            
    if request.method == 'DELETE':
        try:
            db.session.delete(konten)
            db.session.commit()
            return jsonify({"message": "Konten dihapus"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

# ==========================================
# 8. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)