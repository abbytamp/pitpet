1.⁠ ⁠README utama (root repository)

Project PitPet - Sistem Manajemen Klinik Hewan

Proyek ini adalah sistem manajemen appointment dan grooming berbasis web untuk Klinik Hewan PitPet. Backend menggunakan Django, frontend menggunakan t

# Instalasi
1.⁠ ⁠Clone repository
git clone https://gitlab.cs.ui.ac.id/propensi-2025-2026-genap/kelas-c/kotwis-based/kotwis-based-project-pitpet.git

2.⁠ ⁠Buat virtual environment
python -m venv venv
source venv/bin/activate  (Linux/Mac)
venv\Scripts\activate (Windows)

3.⁠ ⁠Install dependencies
pip install -r requirements.txt

4.⁠ ⁠Migrasi database
python manage.py migrate

5.⁠ ⁠Jalankan server
python manage.py runserver

6.⁠ ⁠Akses aplikasi di browser
http://127.0.0.1:8000/

# Struktur Direktori
/backend -> kode Django (apps, models, views, urls)
/templates -> template HTML untuk frontend
/static -> CSS, JS, image
/manage.py -> file utama Django
/requirements.txt -> dependencies Python
/README.md -> berisi beberapa panduan

# Branching & Workflow
•⁠  ⁠main -> branch produksi/stable
•⁠  ⁠development -> branch untuk integrasi fitur
•⁠  ⁠staging → branch testing sebelum merge ke main
•⁠  ⁠Branch individu -> untuk mengerjakan backlog/fitur masing-masing

# Kontributor
•⁠  ⁠Branch “feature-devina” 
•⁠  ⁠Branch “feature-abby”
•⁠  ⁠Branch “feature-amirah”
•⁠  ⁠Branch “feature-salsabila”
•⁠  ⁠Branch “feature-aliyah”