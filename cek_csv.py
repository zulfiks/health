import pandas as pd
import os

# Mencari lokasi file
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, 'data_files', 'data.csv')

print(f"--- MENGECEK FILE CSV ---")
print(f"Lokasi yang dicari: {csv_path}")

if os.path.exists(csv_path):
    print("✅ FILE DITEMUKAN!")
    try:
        df = pd.read_csv(csv_path)
        print(f"✅ FILE TERBACA! Total Data: {len(df)} baris")
        print("--- CONTOH 5 DATA PERTAMA ---")
        print(df[['name', 'calories']].head())
        print("-----------------------------")
        
        # Cek nama kolom
        print("NAMA KOLOM:", df.columns.tolist())
        
        # Tes cari 'Ayam'
        hasil = df[df['name'].str.lower().str.contains('ayam')]
        print(f"Tes Cari 'ayam': Ditemukan {len(hasil)} data.")
    except Exception as e:
        print(f"❌ ERROR SAAT MEMBACA: {e}")
else:
    print("❌ FILE TIDAK DITEMUKAN!")
    print("Pastikan kamu sudah membuat folder 'data_files' dan memasukkan 'data.csv' ke dalamnya.")