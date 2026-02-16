# Sistem Manajemen Layanan Grooming PitPet
Amirah Rizkita Setiadji
2306275235

## Fitur 5: Manajemen Booking Grooming

### Deskripsi Fitur
Fitur **Manajemen Booking Grooming** memungkinkan customer untuk melakukan booking layanan grooming bagi hewan peliharaan mereka. Sistem ini mencakup berbagai langkah mulai dari pemilihan hewan, jenis layanan, paket grooming, hingga pemilihan groomer dan slot waktu. Setelah booking berhasil dibuat, sistem akan menampilkan ringkasan booking yang mencakup ID booking, tanggal, waktu, lokasi, dan total harga. Selain itu, customer dapat melakukan **reschedule** dan **cancel** booking sesuai kebutuhan.

### Aktor yang Terlibat
- **Customer**: Dapat melakukan booking, reschedule, dan cancel booking grooming.
- **Staf Operasional**: Dapat melihat, mengupdate, dan membatalkan booking sesuai kebutuhan operasional.
- **Manager**: Dapat melihat riwayat dan daftar booking untuk kebutuhan monitoring.

### Alur Kerja Fitur
1. **Create Booking** (Role: Customer)
   - **Login** ke sistem dan memilih **hewan peliharaan** untuk grooming.
   - Memilih **jenis layanan** (Home atau Clinic).
   - Memilih **paket grooming** yang diinginkan.
   - **Memilih slot jadwal** dan **groomer** yang tersedia.
   - Mengisi **detail tambahan** sesuai jenis layanan (alamat  dan catatan jika home grooming, catatan jika clinic).
   - **Konfirmasi booking** dan menampilkan **ringkasan booking**.

2. **Read Booking**
   - Customer dapat **melihat daftar booking** mereka dan **detail booking**.
   - Staf operasional dan manager dapat melihat seluruh **daftar booking** untuk kebutuhan monitoring.

3. **Update Booking (Reschedule)**
   - Customer dapat **reschedule** booking dengan memilih slot baru yang tersedia.
   - Sistem memvalidasi slot baru dan memperbarui status booking.

4. **Delete Booking (Cancel)**
   - Customer dapat **membatalkan booking** sesuai aturan yang disepakati.
   - Pembatalan booking mengubah status menjadi **cancelled** dan mengosongkan slot untuk bisa dipilih customer lain.

### Aturan Bisnis (Business Rules)
- Booking hanya dapat dibuat pada slot yang statusnya **tersedia**.
- Groomer yang dapat dipilih harus sesuai dengan jenis layanan yang dipilih oleh customer.
- Reschedule hanya bisa dilakukan ke slot yang **tersedia**.
- Pembatalan akan mengosongkan slot yang sebelumnya terpakai.
- **Status booking**:
  - **Scheduled**: Booking dibuat.
  - **Cancelled**: Booking dibatalkan.
  - **Completed**: Layanan selesai.
  - **In Progress**: Saat layanan sedang berlangsung.
  - **Rescheduled**: Jika jadwal diubah.

### Keterkaitan dengan Fitur Lain
- Menggunakan **slot dari fitur manajemen jadwal kerja dan slot grooming**.
- Status layanan akan diperbarui melalui **fitur dashboard groomer** dan update status layanan.
- **Booking yang selesai** akan masuk ke **riwayat layanan per hewan**.

---

## Fitur 7: Riwayat Layanan per Hewan

### Deskripsi Fitur
Fitur **Riwayat Layanan per Hewan** memungkinkan customer dan staf operasional untuk melihat riwayat layanan grooming yang telah dilakukan pada hewan peliharaan. Riwayat ini bersifat **read-only** dan hanya menampilkan data historis dari layanan grooming yang sudah selesai. Fitur ini membantu customer untuk melihat **rekam jejak perawatan** hewan mereka, serta membantu staf operasional dalam menelusuri riwayat layanan jika terjadi keluhan atau untuk analisis lebih lanjut.

### Aktor yang Terlibat
- **Customer**: Dapat melihat riwayat layanan grooming untuk hewan peliharaannya.
- **Staf Operasional**: Dapat melihat riwayat layanan untuk seluruh hewan dalam sistem untuk keperluan monitoring.
- **Groomer**: Mencatat hasil layanan grooming, yang kemudian akan disimpan dalam riwayat layanan.

### Alur Kerja Fitur
1. **Tampilan Daftar Riwayat per Hewan**
   - Customer dapat memilih salah satu hewan miliknya.
   - Sistem menampilkan daftar **riwayat layanan grooming** yang telah selesai, mencakup:
     - Tanggal grooming
     - Jenis layanan (Home / Clinic)
     - Nama groomer
     - Paket grooming
     - Status (Completed)

2. **Detail Riwayat Layanan**
   - Jika customer memilih salah satu histori, sistem akan menampilkan **detail layanan**, termasuk:
     - Tanggal dan jam layanan
     - Jenis layanan (Home / Clinic)
     - Paket grooming
     - Nama groomer
     - Catatan hasil grooming dari groomer, seperti:
       - Kondisi bulu
       - Kondisi kulit
       - Kebersihan telinga
       - Kondisi kuku
       - Perilaku hewan
       - Catatan tambahan

### Aturan Bisnis (Business Rules)
- **Riwayat hanya menampilkan layanan grooming dengan status "Completed"**.
- Customer hanya dapat melihat riwayat untuk **hewan miliknya sendiri**.
- Staf operasional dapat melihat riwayat layanan dari **seluruh hewan** untuk keperluan monitoring.
- Data riwayat tidak dapat diubah oleh **customer**.

### Keterkaitan dengan Fitur Lain
- Data riwayat layanan bersumber dari **fitur eksekusi dan dokumentasi layanan grooming**.
- Riwayat layanan hanya muncul setelah **layanan selesai** dan **catatan grooming tersimpan**.
- Data riwayat digunakan sebagai dasar untuk **laporan operasional dan statistik**.
