Nama : Abby Shelley Tampubolon
NPM : 2306275254

Fitur 1 — Manajemen Profil Customer dan Data Hewan Peliharaan

Fitur Manajemen Profil Customer dan Data Hewan Peliharaan memungkinkan customer untuk mengelola profil akun serta data hewan peliharaan secara mandiri melalui sistem PitPet.
Customer dapat:
- Menambahkan data hewan baru
- Mengubah data hewan yang sudah terdaftar
- Menghapus data hewan (dengan batasan tertentu)
Setiap customer dapat memiliki lebih dari satu hewan peliharaan, dan seluruh data hewan akan digunakan secara terintegrasi dalam proses booking, dokumentasi layanan, serta riwayat grooming.

Tujuan fitur: 
1. Memberikan kontrol penuh kepada customer dalam mengelola data hewan peliharaan.
2. Mengurangi pencatatan manual melalui WhatsApp dan spreadsheet.
3. Menyediakan data hewan yang terstruktur dan terdokumentasi dengan baik.
4. Mendukung integrasi fitur booking dan histori layanan grooming.

Problem yang terselesaikan :
1. Sebelum fitur ini tersedia:
2. Data hewan dicatat secara manual dan tidak konsisten.
3. Customer harus mengisi ulang data setiap kali melakukan booking.
4. Tingkat kesalahan pencatatan cukup tinggi.
5. Tidak tersedia histori grooming yang terstruktur per hewan.

Value yang Diberikan
- Untuk Customer
1. Tidak perlu mengisi ulang data hewan setiap booking.
2. Data tersimpan rapi dan konsisten.
3. Memiliki histori grooming yang terstruktur per hewan.
4. Proses booking menjadi lebih cepat dan efisien.
- Untuk Operasional
1. Data hewan tervalidasi dalam sistem terpusat.
2. Mengurangi risiko kesalahan pencatatan.
3. Mendukung dokumentasi layanan secara sistematis.

Data Structure (Minimum Fields)
Setiap data hewan mencakup:
1. Nama Hewan (required)
2. Jenis Hewan: Cat / Dog (required)
3. Ras (required)
4. Usia (required)
5. Berat (required)
6. Catatan Tambahan (optional)



FItur 9 — Review dan Rating Layanan

Fitur Review dan Rating Layanan memungkinkan customer memberikan penilaian terhadap layanan grooming yang telah selesai dilakukan.
Review terdiri dari:
- Rating skala 1–5 (wajib)
- Komentar tertulis (opsional)
- Review hanya dapat diberikan untuk booking dengan status Service Completed.

Tujuan Fitur
1. Menyediakan wadah resmi untuk customer menyampaikan umpan balik.
2. Membantu manajemen PitPet mengevaluasi dan meningkatkan kualitas layanan.
3. Menyediakan data kepuasan customer yang terstruktur dan terdokumentasi.

Problem yang Diselesaikan
Sebelumnya:
1. Feedback disampaikan secara informal melalui chat pribadi.
2. Tidak ada dokumentasi terstruktur.
3. Manajemen kesulitan mengukur performa layanan dan groomer
4. Tidak tersedia data untuk analisis kepuasan berkala.

Value yang Diberikan
Untuk Customer
1. Dapat menyampaikan pengalaman layanan secara resmi.
2. Merasa didengar dan dihargai.
3. Rating membantu customer lain memahami kualitas layanan.
Untuk Manajemen
1. Memiliki data evaluasi terstruktur.
2. Dapat memonitor performa groomer.
3. Mendukung peningkatan kualitas layanan.


Data Relationship
Setiap review akan terhubung dengan:
1. Nama customer yang melakukan booking
2. Nama Groomer
3. Paket Layanan
4. Tanggal Layanan
Review dapat diakses oleh staff operasional dan manajer sesuai hak akses.