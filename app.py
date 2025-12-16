from flask import Flask, jsonify, request
from flask_cors import CORS
# Import DB dari extensions
from extensions import db 
# Import Semua Model (Pastikan models.py sudah benar)
from models import Laporan, Admin, Konten, Pengguna, RiwayatAktivitas, RiwayatMakan, Makanan
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

# ==========================================
# 1. KONFIGURASI DATABASE (STABIL XAMPP)
# ==========================================
# Pakai 127.0.0.1 dan Port 3306 agar tidak nyasar
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:@127.0.0.1:3306/healthify"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- SETTING ANTI PUTUS (WAJIB) ---
app.config["SQLALCHEMY_POOL_RECYCLE"] = 299  # Refresh koneksi tiap 5 menit
app.config["SQLALCHEMY_POOL_PRE_PING"] = True # Cek koneksi sebelum query

# ==========================================
# 2. INIT APP
# ==========================================
CORS(app, resources={r"/api/*": {"origins": "*"}})
db.init_app(app) 

# Buat tabel otomatis jika belum ada
with app.app_context():
    db.create_all()
    print("[INFO] Database & Tabel Siap!")

## app.py

@app.route('/api/login/admin', methods=['POST'])
def login_admin():
    data = request.get_json()
    email_admin = data.get('email')
    password_admin = data.get('password') # Ini password dari input user (React)
    
    print(f"\n[LOGIN ADMIN] Mencoba login: {email_admin}")

    # Cek di tabel Admin
    admin = Admin.query.filter_by(email=email_admin).first()

    # PERBAIKAN DI SINI:
    # Gunakan 'admin.password_hash' sesuai nama di models.py
    if admin and str(admin.password_hash) == str(password_admin):
        return jsonify({
            "status": "success", 
            "message": "Login Admin Berhasil!", 
            "user": admin.to_dict()
        }), 200
    else:
        return jsonify({"message": "Email atau Password Admin Salah"}), 401
    
# ==========================================
# 3. HELPER: PATH CSV
# ==========================================
def get_csv_path():
    # Gunakan absolute path biar tidak salah folder
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'data_files', 'data.csv')

# ==========================================
# 4. API SEARCH MAKANAN (CSV)
# ==========================================
@app.route('/api/makanan/search', methods=['GET'])
def search_makanan():
    try:
        query = request.args.get('q', '').lower().strip()
        csv_path = get_csv_path()
        
        if not os.path.exists(csv_path):
            print(f"[ERROR] File CSV tidak ditemukan di: {csv_path}")
            return jsonify([]), 200 

        df = pd.read_csv(csv_path).fillna('')
        df.columns = df.columns.str.strip()
        
        if 'name' in df.columns:
            df['name'] = df['name'].astype(str)
            if query:
                # Cari yang mengandung kata kunci
                df = df[df['name'].str.lower().str.contains(query)]
            
            # Ambil 50 hasil teratas
            result = df.head(50).to_dict(orient='records')
            return jsonify(result), 200
        else:
            return jsonify([]), 200

    except Exception as e:
        print(f"[ERROR] Search Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# 5. API RIWAYAT MAKAN (AUTO ADD POINTS)
# ==========================================
@app.route('/api/riwayat/makan', methods=['POST'])
def add_riwayat_makan():
    try:
        data = request.get_json()
        
        # 1. Simpan Data Makanan
        new_riwayat = RiwayatMakan(
            user_id=data['user_id'],
            nama_makanan=data['nama_makanan'],
            kalori=int(data['kalori']),
            protein=float(data['proteins']),
            lemak=float(data['fat']),
            karbo=float(data['carbohydrate']),
            waktu_makan=data['waktu'],
            tanggal=datetime.now().strftime("%Y-%m-%d")
        )
        db.session.add(new_riwayat)
        
        # 2. UPDATE POIN USER (REAL-TIME)
        # Tambah 5 Poin setiap input makanan
        user = Pengguna.query.get(data['user_id'])
        if user:
            user.poin += 5 
        
        db.session.commit()
        
        return jsonify({
            "message": "Berhasil! +5 Poin ditambahkan.", 
            "data": new_riwayat.to_dict(),
            "total_poin": user.poin 
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ==========================================
# 6. API SUMMARY HARIAN (TARGET BMR)
# ==========================================
@app.route('/api/summary/<int:user_id>', methods=['GET'])
def get_daily_summary(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Ambil Data User untuk Hitung Target BMR
    user = Pengguna.query.get_or_404(user_id)
    
    target_kalori = 2000 # Default
    
    # Rumus Mifflin-St Jeor
    if user.berat > 0 and user.tinggi > 0 and user.umur > 0:
        if user.gender == 'L':
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) + 5
        else:
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) - 161
        
        target_kalori = int(target_kalori * 1.2) # Aktivitas Sedang
    
    # 2. Hitung Total Makan Hari Ini
    riwayat = RiwayatMakan.query.filter_by(user_id=user_id, tanggal=today).all()
    total_kalori = sum(r.kalori for r in riwayat)
    
    # 3. Status Gizi (Visual)
    if target_kalori == 0: target_kalori = 2000
    persentase = (total_kalori / target_kalori) * 100
    
    status_gizi = "Belum Cukup"
    poin_dapat = 0 # Poin visual hari ini (akumulasi sudah di user.poin)
    pesan_motivasi = "Ayo makan sehat!"

    if total_kalori == 0:
         status_gizi = "Belum Makan"
         pesan_motivasi = "Jangan lupa sarapan ya!"
    elif persentase < 50:
        status_gizi = "Kurang Energi ⚠️"
        poin_dapat = 1
        pesan_motivasi = "Tubuhmu butuh bensin, ayo makan lagi."
    elif persentase >= 50 and persentase < 80:
        status_gizi = "Hampir Cukup 😐"
        poin_dapat = 2
        pesan_motivasi = "Sedikit lagi mencapai target!"
    elif persentase >= 80 and persentase <= 110:
        status_gizi = "Ideal / Bagus ✨"
        poin_dapat = 3
        pesan_motivasi = "Luar biasa! Pertahankan gizimu."
    else:
        status_gizi = "Berlebihan 🛑"
        poin_dapat = 1
        pesan_motivasi = "Ups, rem dulu makannya ya."

    # Pisahkan per waktu makan
    list_pagi = [r.to_dict() for r in riwayat if r.waktu_makan == 'Pagi']
    list_siang = [r.to_dict() for r in riwayat if r.waktu_makan == 'Siang']
    list_malam = [r.to_dict() for r in riwayat if r.waktu_makan == 'Malam']

    return jsonify({
        "total_kalori": total_kalori,
        "target_kalori": target_kalori, 
        "status_gizi": status_gizi,     
        "poin_hari_ini": poin_dapat,    
        "pesan": pesan_motivasi,        
        "pagi": list_pagi,
        "siang": list_siang,
        "malam": list_malam
    }), 200

# ==========================================
# 7. API USERS & LEADERBOARD
# ==========================================
@app.route('/api/users', methods=['GET'])
def get_users():
    # Ambil semua user untuk Leaderboard
    all_users = Pengguna.query.all()
    return jsonify([u.to_dict() for u in all_users]), 200

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    cek_email = Pengguna.query.filter_by(email=data['email']).first()
    if cek_email:
        return jsonify({"message": "Email sudah terdaftar!"}), 400

    new_user = Pengguna(
        nama=data['nama'], email=data['email'], password=data['password'],
        umur=0, gender='-', tinggi=0, berat=0, poin=0
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registrasi Berhasil!", "user": new_user.to_dict()}), 201

@app.route('/api/login/user', methods=['POST'])
def login_user():
    data = request.get_json()
    email_hp = data.get('email')
    password_hp = data.get('password')
    
    print(f"\n[LOGIN] Mencoba login: {email_hp}")

    user = Pengguna.query.filter_by(email=email_hp).first()

    if user and str(user.password) == str(password_hp):
        return jsonify({"status": "success", "message": "Login User Berhasil!", "user": user.to_dict()}), 200
    else:
        return jsonify({"message": "Email atau Password Salah"}), 401

@app.route('/api/users/<int:id>', methods=['GET'])
def get_user_detail(id):
    user = Pengguna.query.get_or_404(id)
    return jsonify(user.to_dict()), 200

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    user = Pengguna.query.get_or_404(id)
    data = request.get_json()
    
    if 'nama' in data: user.nama = data['nama']
    if 'email' in data: user.email = data['email']
    if 'gender' in data: user.gender = data['gender']
    if 'umur' in data: user.umur = int(data['umur'])
    if 'tinggi' in data: user.tinggi = int(data['tinggi'])
    if 'berat' in data: user.berat = int(data['berat'])
    if 'poin' in data: user.poin = int(data['poin']) # Bisa update poin manual juga
    if 'password' in data and data['password'] != "":
        user.password = data['password']

    db.session.commit()
    return jsonify({"message": "Data Berhasil Diupdate!", "user": user.to_dict()}), 200

# ==========================================
# 8. API KONTEN & LAPORAN
# ==========================================
@app.route('/api/konten', methods=['GET'])
def get_konten():
    return jsonify([item.to_dict() for item in Konten.query.all()]), 200

@app.route('/api/konten', methods=['POST'])
def add_konten():
    d = request.get_json()
    new = Konten(
        judul=d['judul'], kategori=d['kategori'], 
        publikasi=d['publikasi'], tautan=d['tautan'],
        foto=d.get('foto', '')
    )
    db.session.add(new)
    db.session.commit()
    return jsonify({"message": "Added", "data": new.to_dict()}), 201

@app.route('/api/laporan', methods=['POST'])
def add_laporan():
    nama = request.form.get('nama')
    email = request.form.get('email')
    jenis = request.form.get('jenis')
    deskripsi = request.form.get('deskripsi')
    final_desc = f"[{jenis}] {deskripsi} (Email: {email})"
    
    filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = file.filename 

    new_laporan = Laporan(
        pengguna=nama, tanggal=datetime.now().strftime("%Y-%m-%d"),
        deskripsi=final_desc, status="Pending", image=filename
    )
    db.session.add(new_laporan)
    db.session.commit()
    return jsonify({"message": "Laporan Terkirim!"}), 201

@app.route('/api/laporan', methods=['GET'])
def get_laporan():
    return jsonify([d.to_dict() for d in Laporan.query.all()])

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)