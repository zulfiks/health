from flask import Flask, jsonify, request
from flask_cors import CORS
# Import DB dari extensions
from extensions import db 
# Import Semua Model (Pastikan models.py sudah update ada kolom email/jenis)
from models import Laporan, Admin, Konten, Pengguna, RiwayatAktivitas, RiwayatMakan, Makanan, RiwayatLari
import pandas as pd
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

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

# ==========================================
# 3. API ADMIN
# ==========================================
@app.route('/api/login/admin', methods=['POST'])
def login_admin():
    data = request.get_json()
    email_admin = data.get('email')
    password_admin = data.get('password') 
    
    # Debugging: Cek apa yang diterima server di Terminal
    print(f"[DEBUG] Login Admin: Email={email_admin} | PassInput={password_admin}")

    # Cek di tabel Admin
    admin = Admin.query.filter_by(email=email_admin).first()

    # LOGIKA POLOS (TANPA HASH)
    if admin:
        # Debugging: Cek apa isi password di database
        print(f"[DEBUG] Password di DB: {admin.password_hash}")
        
        # Bandingkan langsung string ketemu string
        if str(admin.password_hash) == str(password_admin):
            return jsonify({
                "status": "success", 
                "message": "Login Admin Berhasil!", 
                "user": admin.to_dict()
            }), 200
    
    return jsonify({"message": "Email atau Password Admin Salah"}), 401

@app.route('/api/admin/profile', methods=['GET'])
def get_admin_profile():
    try:
        # Ambil parameter email dari URL (?email=...)
        email = request.args.get('email')
        if not email:
            return jsonify({"message": "Email diperlukan"}), 400

        admin = Admin.query.filter_by(email=email).first()
        
        if not admin:
            return jsonify({"message": "Admin tidak ditemukan"}), 404
            
        return jsonify(admin.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/profile', methods=['PUT'])
def update_admin_profile():
    try:
        data = request.get_json()
        
        # Cari admin berdasarkan email lama (karena email unik)
        email_lama = data.get('email_lama')
        admin = Admin.query.filter_by(email=email_lama).first()
        
        if not admin:
            return jsonify({"message": "Akun admin tidak ditemukan"}), 404

        # 1. Update Nama
        if 'nama' in data:
            admin.nama = data['nama']

        # 2. Update Password (Hanya jika ada request ganti password)
        password_baru = data.get('password_baru')
        password_lama = data.get('password_lama')

        if password_baru:
            # KEAMANAN: Cek dulu apakah password lama benar
            # (Sesuaikan logic ini dengan cara kamu menyimpan password di login_admin)
            if str(admin.password_hash) != str(password_lama):
                return jsonify({"message": "Gagal: Password lama salah!"}), 401
            
            # Jika benar, simpan password baru
            admin.password_hash = password_baru

        db.session.commit()
        return jsonify({"message": "Profil berhasil diperbarui", "user": admin.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR UPDATE ADMIN] {e}")
        return jsonify({"error": str(e)}), 500
    
# ==========================================
# 4. API SEARCH & CRUD MAKANAN
# ==========================================
@app.route('/api/makanan/search', methods=['GET'])
def search_makanan():
    try:
        query_param = request.args.get('q', '').strip()
        if not query_param:
            return jsonify([]), 200

        hasil_cari = Makanan.query.filter(Makanan.name.ilike(f"%{query_param}%")).limit(50).all()
        data_json = [item.to_dict() for item in hasil_cari]
        
        return jsonify(data_json), 200
    except Exception as e:
        print(f"[ERROR] Database Search Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/makanan', methods=['GET'])
def get_all_makanan():
    try:
        semua_makanan = Makanan.query.all()
        return jsonify([item.to_dict() for item in semua_makanan]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/makanan', methods=['POST'])
def add_new_makanan():
    try:
        data = request.get_json()
        new_food = Makanan(
            name=data['name'],
            calories=float(data['calories']),
            proteins=float(data['proteins']),
            fat=float(data['fat']),
            carbohydrate=float(data['carbohydrate']),
            image=data['image']
        )
        db.session.add(new_food)
        db.session.commit()
        return jsonify({"message": "Berhasil ditambahkan", "data": new_food.to_dict()}), 201
    except Exception as e:
        db.session.rollback() 
        return jsonify({"error": str(e)}), 500

@app.route('/api/makanan/<int:id>', methods=['PUT'])
def update_makanan(id):
    try:
        food = Makanan.query.get_or_404(id)
        data = request.get_json()
        
        if 'name' in data: food.name = data['name']
        if 'calories' in data: food.calories = float(data['calories'])
        if 'proteins' in data: food.proteins = float(data['proteins'])
        if 'fat' in data: food.fat = float(data['fat'])
        if 'carbohydrate' in data: food.carbohydrate = float(data['carbohydrate'])
        if 'image' in data: food.image = data['image']
        
        db.session.commit()
        return jsonify({"message": "Berhasil diupdate", "data": food.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/makanan/<int:id>', methods=['DELETE'])
def delete_makanan(id):
    try:
        food = Makanan.query.get_or_404(id)
        db.session.delete(food)
        db.session.commit()
        return jsonify({"message": "Berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# ==========================================
# 5. API RIWAYAT MAKAN
# ==========================================
@app.route('/api/riwayat/makan', methods=['POST'])
def add_riwayat_makan():
    try:
        data = request.get_json()
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
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# ==========================================
# 6. API SUMMARY HARIAN
# ==========================================
@app.route('/api/summary/<int:user_id>', methods=['GET'])
def get_daily_summary(user_id):
    today = datetime.now().strftime("%Y-%m-%d")
    user = Pengguna.query.get_or_404(user_id)
    
    target_kalori = 2000 
    if user.berat > 0 and user.tinggi > 0 and user.umur > 0:
        if user.gender == 'L':
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) + 5
        else:
            target_kalori = (10 * user.berat) + (6.25 * user.tinggi) - (5 * user.umur) - 161
        target_kalori = int(target_kalori * 1.2) 
    
    riwayat = RiwayatMakan.query.filter_by(user_id=user_id, tanggal=today).all()
    total_kalori = sum(r.kalori for r in riwayat)
    
    if target_kalori == 0: target_kalori = 2000
    persentase = (total_kalori / target_kalori) * 100
    
    status_gizi = "Belum Cukup"
    poin_dapat = 0 
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
# 7. API USERS
# ==========================================
@app.route('/api/users', methods=['GET'])
def get_users():
    all_users = Pengguna.query.all()
    return jsonify([u.to_dict() for u in all_users]), 200

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    cek_email = Pengguna.query.filter_by(email=data['email']).first()
    if cek_email:
        return jsonify({"message": "Email sudah terdaftar!"}), 400

    # --- BAGIAN HASHING MAKSIMAL ---
    # method='pbkdf2:sha256' adalah standar keamanan tinggi saat ini
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')

    new_user = Pengguna(
        nama=data['nama'], 
        email=data['email'], 
        password=hashed_password, # Simpan yang sudah di-hash
        umur=0, gender='-', tinggi=0, berat=0, poin=0
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registrasi Berhasil!", "user": new_user.to_dict()}), 201

@app.route('/api/login/user', methods=['POST'])
def login_user():
    data = request.get_json()
    email_hp = data.get('email')
    password_input = data.get('password') # Password dari inputan User
    
    print(f"\n[LOGIN] Mencoba login: {email_hp}")

    user = Pengguna.query.filter_by(email=email_hp).first()

    # Cek user ada ATAU TIDAK
    if not user:
        return jsonify({"message": "Email tidak ditemukan"}), 401

    # --- LOGIKA CEK PASSWORD ---
    password_is_valid = False

    # Cek 1: Apakah password di DB sudah di-hash? (Biasanya panjang > 50 karakter)
    if len(user.password) > 50 and user.password.startswith('pbkdf2:'):
        # Gunakan pengecekan aman
        if check_password_hash(user.password, password_input):
            password_is_valid = True
    else:
        # Cek 2: Fallback untuk user lama (seperti Rizki/Liana) yang passwordnya masih "1234"
        # Ini supaya user lama TETAP BISA LOGIN sebelum migrasi
        if str(user.password) == str(password_input):
            password_is_valid = True
            
            # OPSIONAL: Otomatis update password mereka ke hash biar aman ke depannya
            user.password = generate_password_hash(password_input, method='pbkdf2:sha256')
            db.session.commit()
            print(f"[INFO] Password user {user.nama} berhasil di-upgrade ke Hash aman.")

    if password_is_valid:
        return jsonify({
            "status": "success", 
            "message": "Login User Berhasil!", 
            "user": user.to_dict()
        }), 200
    else:
        return jsonify({"message": "Password Salah"}), 401
    
@app.route('/api/fix-passwords', methods=['GET'])
def fix_passwords():
    users = Pengguna.query.all()
    count = 0
    for u in users:
        # Jika password belum di-hash (pendek, misal "1234")
        if len(u.password) < 50:
            print(f"Mengamankan password user: {u.nama}")
            # Hash password lama mereka
            u.password = generate_password_hash(u.password, method='pbkdf2:sha256')
            count += 1
    
    db.session.commit()
    return jsonify({"message": f"Berhasil mengamankan {count} akun user lama!"}), 200

@app.route('/api/users/<int:id>', methods=['GET'])
def get_user_detail(id):
    try:
        user = Pengguna.query.get_or_404(id)
        data = user.to_dict()

        # Hitung BMI di Server (Biar Dart terima beres)
        if user.tinggi > 0 and user.berat > 0:
            t_meter = user.tinggi / 100
            data['bmi_score'] = round(user.berat / (t_meter * t_meter), 1)
        else:
            data['bmi_score'] = 0

        # Fix URL Foto
        if user.foto:
             data['foto'] = f"http://192.168.1.7:5000/static/uploads/{user.foto}"
             
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    try:
        user = Pengguna.query.get_or_404(id)
        
        # --- LOGIKA PINTAR (HYBRID HANDLER) ---
        # Cek apakah request datang dari BMI Screen (JSON) atau Profile Screen (Multipart/Form)
        data = {}
        is_json = False

        if request.is_json:
            # Ini dari BMI Screen
            data = request.get_json()
            is_json = True
            print(f"[DEBUG] Update via JSON (BMI Screen): {data}")
        else:
            # Ini dari Profile Screen (Form Data)
            data = request.form
            print(f"[DEBUG] Update via Form (Profile Screen): {data}")

        # 1. Update Data Dasar (Cek key ada atau tidak sebelum update)
        if 'nama' in data: user.nama = data['nama']
        if 'email' in data: user.email = data['email']
        if 'gender' in data: user.gender = data['gender']
        
        # 2. Update Statistik Tubuh (Penting untuk Sinkronisasi BMI)
        # Kita pakai float() biar aman kalau dikirim string atau angka
        if 'umur' in data and data['umur']: 
            user.umur = int(float(data['umur']))
        if 'tinggi' in data and data['tinggi']: 
            user.tinggi = float(data['tinggi'])
        if 'berat' in data and data['berat']: 
            user.berat = float(data['berat'])

        # 3. Update Foto (Hanya bisa dari Profile Screen / Form)
        if not is_json and 'foto' in request.files:
            file = request.files['foto']
            if file.filename != '':
                # Hapus foto lama jika ada (opsional, biar server gak penuh)
                # if user.foto and os.path.exists(os.path.join(app.root_path, 'static/uploads', user.foto)):
                #     os.remove(os.path.join(app.root_path, 'static/uploads', user.foto))

                filename = f"user_{id}_{int(datetime.now().timestamp())}.jpg"
                upload_folder = os.path.join(app.root_path, 'static/uploads')
                
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                    
                file.save(os.path.join(upload_folder, filename))
                user.foto = filename 

        # 4. Update Password (Logika Aman)
        if 'password' in data and data['password']:
            new_pass_input = data['password']
            old_pass_input = data.get('old_password') # Bisa None kalau dari BMI screen
            
            # Jika update password, password lama WAJIB dikirim (Logic Profile Screen)
            if old_pass_input:
                password_match = False
                if user.password.startswith('pbkdf2:'):
                    if check_password_hash(user.password, old_pass_input):
                        password_match = True
                else:
                    if str(user.password) == str(old_pass_input):
                        password_match = True
                
                if password_match:
                    user.password = generate_password_hash(new_pass_input, method='pbkdf2:sha256')
                else:
                    return jsonify({"message": "Password lama salah!"}), 401

        db.session.commit()
        
        # Siapkan respon data terbaru
        user_dict = user.to_dict()
        if user.foto:
            # Pastikan IP ini sesuai dengan Laptop kamu
            user_dict['foto'] = f"http://192.168.1.7:5000/static/uploads/{user.foto}"

        return jsonify({"message": "Data Berhasil Diupdate!", "user": user_dict}), 200

    except Exception as e:
        db.session.rollback()
        print(f"[ERROR UPDATE USER] {e}") 
        return jsonify({"message": "Gagal update data", "error": str(e)}), 500

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

@app.route('/api/laporan', methods=['GET'])
def get_laporan():
    return jsonify([d.to_dict() for d in Laporan.query.all()])

# --- BAGIAN PENTING: SUDAH DIPERBAIKI (Tidak Duplikat Lagi) ---
@app.route('/api/laporan', methods=['POST'])
def add_laporan():
    nama = request.form.get('nama')
    email = request.form.get('email')
    jenis = request.form.get('jenis')
    deskripsi = request.form.get('deskripsi')
    
    filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            filename = file.filename
            
            # PASTIIN FOLDERNYA ADA DULU
            upload_folder = os.path.join(app.root_path, 'static/uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # SIMPAN FILE FISIK
            file.save(os.path.join(upload_folder, filename)) 

    new_laporan = Laporan(
        pengguna=nama, email=email, jenis=jenis,
        tanggal=datetime.now().strftime("%Y-%m-%d"),
        deskripsi=deskripsi, status="Pending", image=filename
    )
    
    db.session.add(new_laporan)
    db.session.commit()
    return jsonify({"message": "Laporan Terkirim!"}), 201

# 2. TAMBAH ROUTE BARU UNTUK GANTI STATUS
@app.route('/api/laporan/<int:id>/status', methods=['PUT'])
def update_status_laporan(id):
    laporan = Laporan.query.get_or_404(id)
    data = request.get_json()
    
    # Update status (misal: dari Pending -> Selesai)
    laporan.status = data['status']
    
    db.session.commit()
    return jsonify({"message": "Status berhasil diupdate!"}), 200
@app.route('/api/laporan/<int:id>', methods=['DELETE'])
def delete_laporan(id):
    try:
        laporan = Laporan.query.get_or_404(id)
        
        # Opsi Tambahan: Hapus file gambar dari folder jika ada
        if laporan.image:
            file_path = os.path.join(app.root_path, 'static/uploads', laporan.image)
            if os.path.exists(file_path):
                os.remove(file_path)
                
        db.session.delete(laporan)
        db.session.commit()
        return jsonify({"message": "Laporan berhasil dihapus"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
# --- API HISTORY PAKAI FILTER EMAIL ---
@app.route('/api/riwayat-laporan', methods=['GET'])
def riwayat_laporan():
    # 1. Kita filter berdasarkan EMAIL (Lebih Aman & Pribadi)
    email_user = request.args.get('email') 
    
    try:
        # 2. Query: Cari di tabel Laporan yang email-nya COCOK
        hasil_db = Laporan.query.filter_by(email=email_user).order_by(Laporan.tanggal.desc()).all()
        
        payload = []
        for item in hasil_db:
            payload.append({
                'jenis': item.jenis,          
                'deskripsi': item.deskripsi,  
                'tanggal': str(item.tanggal), 
                'status': item.status
            })
            
        return jsonify(payload), 200
        
    except Exception as e:
        print(f"Error Database: {e}")
        return jsonify({"message": "Gagal mengambil data", "error": str(e)}), 500

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    try:
        # 1. Cari user berdasarkan ID
        user = Pengguna.query.get_or_404(id)
        
        # 2. Hapus User (Otomatis riwayat makan & aktivitas ikut terhapus karena cascade di models.py)
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({"message": "User dan seluruh riwayatnya berhasil dihapus!"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR DELETE USER] {e}")
        return jsonify({"error": str(e), "message": "Gagal menghapus user"}), 500

# --- TAMBAHKAN INI DI BAWAH add_konten ---

@app.route('/api/konten/<int:id>', methods=['PUT'])
def update_konten(id):
    try:
        item = Konten.query.get_or_404(id)
        data = request.get_json()
        
        if 'judul' in data: item.judul = data['judul']
        if 'kategori' in data: item.kategori = data['kategori']
        if 'publikasi' in data: item.publikasi = data['publikasi']
        if 'tautan' in data: item.tautan = data['tautan']
        if 'foto' in data: item.foto = data['foto'] # Update Foto juga
        
        db.session.commit()
        return jsonify({"message": "Konten berhasil diupdate"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/konten/<int:id>', methods=['DELETE'])
def delete_konten(id):
    try:
        item = Konten.query.get_or_404(id)
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Konten berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/reset-password/verify', methods=['POST'])
def verify_user_reset():
    data = request.get_json()
    nama = data.get('nama')
    email = data.get('email')

    # Cari user yang nama DAN email-nya cocok
    user = Pengguna.query.filter_by(nama=nama, email=email).first()

    if user:
        return jsonify({"status": "success", "message": "User ditemukan", "user_id": user.id}), 200
    else:
        return jsonify({"status": "error", "message": "Nama atau Email tidak terdaftar!"}), 404

@app.route('/api/reset-password/update', methods=['PUT'])
def update_password_reset():
    data = request.get_json()
    user_id = data.get('user_id')
    new_password = data.get('new_password')

    user = Pengguna.query.get(user_id)
    if user:
        # --- PERBAIKAN: HASH PASSWORD SEBELUM DISIMPAN ---
        from werkzeug.security import generate_password_hash # Pastikan ini terimport
        
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        user.password = hashed_password
        
        db.session.commit()
        return jsonify({"status": "success", "message": "Password berhasil diperbarui!"}), 200
    
    return jsonify({"status": "error", "message": "User tidak ditemukan"}), 404

# ==========================================
# 9. API KHUSUS LARI (TRACKING & HISTORY)
# ==========================================

# 1. API UNTUK MENYIMPAN DATA LARI (POST)
@app.route('/api/lari', methods=['POST'])
def add_riwayat_lari():
    try:
        data = request.get_json()
        
        # Logika Poin: Tambah 1 poin setiap kali lari selesai
        poin_dapat = 1 

        new_run = RiwayatLari(
            user_id=data['user_id'],
            jarak=float(data['jarak']),
            waktu=data['waktu'],
            kalori=int(data['kalori']),
            tanggal=datetime.now().strftime("%Y-%m-%d"),
            rute=data.get('rute', 'Lokasi tersimpan')
        )
        
        # Update poin user
        user = Pengguna.query.get(data['user_id'])
        if user:
            user.poin += poin_dapat

        db.session.add(new_run)
        db.session.commit()
        
        return jsonify({
            "message": "Lari berhasil disimpan! +1 Poin", 
            "data": new_run.to_dict(),
            "total_poin": user.poin
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"[ERROR LARI] {e}")
        return jsonify({"error": str(e)}), 500

# 2. API UNTUK MENGAMBIL HISTORY LARI (GET) - INI YANG KEMARIN HILANG
@app.route('/api/lari/<int:user_id>', methods=['GET'])
def get_riwayat_lari(user_id):
    try:
        # Ambil data berdasarkan user_id, urutkan dari yang paling baru (descending)
        items = RiwayatLari.query.filter_by(user_id=user_id).order_by(RiwayatLari.id.desc()).all()
        
        # Ubah ke format JSON biar bisa dibaca Flutter
        return jsonify([item.to_dict() for item in items]), 200
    except Exception as e:
        print(f"[ERROR GET LARI] {e}")
        return jsonify({"error": str(e)}), 500
    
# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)