# Dokumentasi Dashboard Accounting (Bahasa Indonesia)

Dokumen ini menjelaskan fitur dashboard `account_board_dashboard` dengan bahasa sederhana untuk user bisnis/management.

## 1. Tujuan Dashboard
Dashboard ini dibuat untuk membantu BOD/management melihat kesehatan keuangan utama tanpa harus buka banyak report terpisah.

Fokusnya:
- Ringkasan KPI penting
- Risiko (piutang macet, likuiditas)
- Tren performa
- Benchmark antar company
- Drill-down ke data akuntansi detail
- Export PDF untuk rapat

---

## 2. Lokasi Menu
Masuk ke:
- `Dashboard > Accounting`

Akses dikontrol oleh group:
- `Board Accounting Dashboard`

---

## 3. Filter dan Kontrol Atas
Di bagian atas ada kontrol:
- `Period`: `YTD` atau `MTD`
  - `YTD` = Year To Date (dari awal tahun sampai hari ini)
  - `MTD` = Month To Date (dari awal bulan sampai hari ini)
- `Refresh`: ambil data terbaru
- `Export PDF`: cetak laporan board dalam format PDF (server-side report)
- `Theme`: ubah tema tampilan
- `Full Screen`: mode layar penuh untuk presentasi

Juga ada info:
- `Live as of ...` = waktu terakhir dashboard di-refresh
- `Snapshot Date` = tanggal snapshot KPI

---

## 4. Peringatan Multi Mata Uang
Jika beberapa company memakai mata uang berbeda, akan muncul warning:
- `Currency Warning: Mixed currencies detected...`

Artinya total gabungan bisa menyesatkan jika belum dikonversi FX ke 1 mata uang reporting.

---

## 5. KPI Strip (Ringkasan Cepat)
KPI utama yang ditampilkan:
- Revenue (MTD/YTD)
- Gross Profit (MTD/YTD)
- Net Profit (MTD/YTD)
- Cash Balance
- AR Open
- AP Open
- DSO (Days Sales Outstanding)
- DPO (Days Payables Outstanding)
- Quick Ratio

### Arti singkat KPI
- `AR Open`: total piutang belum lunas
- `AP Open`: total hutang belum dibayar
- `DSO`: rata-rata hari penagihan piutang
- `DPO`: rata-rata hari pembayaran ke supplier
- `Quick Ratio`: (Cash + AR) / AP

### Badge status KPI
Setiap KPI punya badge (misal `Healthy`, `Watch`, `Critical`, `Actual`, dll) sebagai indikator cepat, bukan budget attainment.

---

## 6. Revenue Share by Company
Grafik donut menunjukkan komposisi revenue per company.
- Persentase menunjukkan porsi kontribusi terhadap total revenue periode terpilih.
- Klik nama company di legend => drill ke revenue lines (pivot/graph/list).

---

## 7. Top Risk Indicators
Bagian ini menampilkan risiko utama:
- `Overdue AR 90+`
- `Quick Ratio (Cash+AR / AP)`

Ada badge level risiko (`LOW/MEDIUM/HIGH`).
Ada tombol `Drill Overdue Receivables` untuk buka analisis detail overdue AR.

---

## 8. Cash Runway
Panel ini memperlihatkan:
- Total cash saat ini
- Rata-rata OpEx bulanan
- Estimasi runway (berapa bulan cash cukup)

Status:
- `critical` jika runway sangat pendek
- `watch` jika perlu perhatian
- `healthy` jika aman

---

## 9. Aging Buckets Overview
Ringkasan aging dalam bucket:
- Not Due
- 1-30
- 31-60
- 61-90
- 90+

Memudahkan lihat distribusi piutang/hutang berdasarkan umur.

---

## 10. What Changed
Panel insight otomatis (maks 3 poin), contoh:
- Company A revenue naik/turun MoM
- Overdue AR 90+ nilai terbaru

Tujuannya supaya BOD cepat tahu perubahan paling penting.

---

## 11. Consolidated Revenue & Margin Trend
Tabel tren bulanan (hingga 24 bulan):
- Revenue
- Gross Margin %
- Net Margin %

Baris dengan net margin negatif diberi highlight agar cepat terlihat.

---

## 12. Auditability Panel
Panel ini untuk meningkatkan trust data:
- Snapshot Date
- Refreshed timestamp
- Period
- Check konsistensi:
  - Revenue Summary vs Monthly
  - AR Summary vs Aging

Jika selisih terlalu besar, status jadi `WARN`.

---

## 13. Peer Benchmarking
Perbandingan antar company dalam grup:
- Growth %
- Net Margin %
- AR 90+ %
- Delta vs median grup

Tujuannya melihat siapa outperform/underperform secara cepat.

---

## 14. Detailed Views (Collapsible)
Bagian detail tambahan (bisa dibuka/tutup), berisi:
- Profitability ranking
- Decision panel (aksi prioritas berdasarkan kondisi data)

Decision panel sekarang data-driven:
- Hanya muncul tindakan kalau trigger terpenuhi
- Jika sehat semua, muncul “No actions required”

---

## 15. Drill-Down yang Tersedia
1. Klik nama company di `Revenue Share`
   - Buka `account.move.line` view (pivot/graph/list)
   - Domain: posted revenue account
   - Grouping default: partner dan product

2. Klik `Drill Overdue Receivables`
   - Buka overdue AR detail
   - Domain: receivable, residual != 0, maturity lewat hari ini

---

## 16. Export PDF
Tombol `Export PDF` menghasilkan laporan board via QWeb PDF (server-side), lebih konsisten dibanding print browser biasa.

Isi PDF:
- Headline KPIs
- Revenue share
- Consolidated trend
- Risk indicator

---

## 17. Catatan Penting / Batasan Saat Ini
1. Belum ada integrasi budget aktual resmi
   - Jadi belum ada Budget vs Actual real dari modul budget.
2. Jika multi-currency, total konsolidasi belum FX-converted
   - Dashboard sudah kasih warning agar user aware.
3. DSO/DPO/runway adalah indikator operasional
   - Bukan pengganti full financial statement audit report.

---

## 18. Definisi Singkat Istilah
- `MTD`: Month-to-Date
- `YTD`: Year-to-Date
- `AR`: Accounts Receivable (Piutang)
- `AP`: Accounts Payable (Hutang)
- `DSO`: Days Sales Outstanding (hari rata-rata penagihan)
- `DPO`: Days Payables Outstanding (hari rata-rata pembayaran)

---

## 19. Alur Pakai yang Direkomendasikan (untuk BOD Meeting)
1. Pilih period (`MTD` atau `YTD`)
2. Lihat KPI strip + risk indicator + cash runway
3. Cek revenue share dan benchmarking
4. Cek “What Changed” untuk narasi rapat
5. Drill-down jika ada angka anomali
6. Export PDF untuk dokumentasi meeting

---

## 20. Troubleshooting Cepat
Jika dashboard tidak update:
1. Klik `Refresh`
2. Reload browser hard refresh
3. Pastikan module `account_board_dashboard` sudah upgrade versi terbaru
4. Pastikan user punya group `Board Accounting Dashboard`
