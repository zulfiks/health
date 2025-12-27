# Gunakan Python versi ringan
FROM python:3.9-slim

# Set folder kerja di dalam container
WORKDIR /app

# Salin requirements dulu (biar cache efisien)
COPY requirements.txt .

# Install library Python yang dibutuhkan
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua kode backend ke dalam container
COPY . .

# Buka port 5000 (port Flask)
EXPOSE 5000

# Jalankan aplikasi Flask
CMD ["python", "app.py"]