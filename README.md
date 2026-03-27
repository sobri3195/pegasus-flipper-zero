# Pegasus Flipper Zero

Utilitas Python untuk diagnostik **Flipper Zero + Bluetooth** di Linux. Proyek ini berfokus pada observabilitas lokal (scan perangkat, status koneksi, dan RSSI) dengan pendekatan aman: semua aksi bersifat eksplisit melalui flag CLI, tidak ada aksi agresif otomatis.

## Fitur Utama

- **Handshake serial opsional ke Flipper Zero** (`--activate-hid`).
- **Bluetooth scan** perangkat terdekat (`--scan`).
- **Tracking event koneksi/disconnect** berbasis polling (`--track-connections`).
- **RSSI inquiry output** via `hcitool` (`--rssi`).
- Logging event koneksi ke file (`--log-file`, default `connection.log`).

## Struktur Proyek

- `main.py`: Entry point script CLI diagnostik.
- `README.md`: Dokumentasi penggunaan proyek.

## Persyaratan

### 1) Sistem Operasi

Direkomendasikan Linux dengan stack Bluetooth (`bluetoothctl`).

### 2) Python

- Python **3.10+** (disarankan 3.11 atau lebih baru).

### 3) Dependensi Python

- `pyserial` (hanya diperlukan jika memakai fitur serial handshake).

Install:

```bash
python3 -m pip install pyserial
```

### 4) Dependensi Sistem

Pastikan command berikut tersedia sesuai fitur yang dipakai:

- `bluetoothctl` → untuk scan dan cek status koneksi.
- `hcitool` → untuk fitur RSSI inquiry (`--rssi`).

> Catatan: beberapa distro modern tidak lagi memaketkan `hcitool` secara default. Jika tidak tersedia, fitur `--rssi` bisa tidak menghasilkan output.

## Cara Menjalankan

Jalankan script dari root proyek:

```bash
python3 main.py [opsi]
```

Lihat seluruh opsi:

```bash
python3 main.py --help
```

## Opsi CLI

| Opsi | Deskripsi | Default |
|---|---|---|
| `--serial-port` | Port serial untuk handshake Flipper | `/dev/ttyACM0` |
| `--activate-hid` | Kirim byte handshake ke Flipper via serial | `off` |
| `--scan` | Jalankan scan perangkat Bluetooth | `off` |
| `--scan-seconds` | Durasi scan dalam detik | `10` |
| `--track-connections` | Pantau event connect/disconnect | `off` |
| `--track-seconds` | Durasi pemantauan koneksi (detik) | `30` |
| `--poll-interval` | Interval polling koneksi (detik) | `3` |
| `--log-file` | File output log event koneksi | `connection.log` |
| `--rssi` | Cetak RSSI inquiry (`hcitool`) | `off` |

## Contoh Penggunaan

### 1) Scan perangkat selama 15 detik

```bash
python3 main.py --scan --scan-seconds 15
```

### 2) Pantau event koneksi selama 2 menit

```bash
python3 main.py --track-connections --track-seconds 120 --poll-interval 5
```

### 3) Simpan log ke file khusus

```bash
python3 main.py --track-connections --log-file logs/bt-events.log
```

### 4) Jalankan RSSI inquiry

```bash
python3 main.py --rssi
```

### 5) Kirim handshake ke Flipper di port tertentu

```bash
python3 main.py --activate-hid --serial-port /dev/ttyACM1
```

### 6) Gabungkan beberapa fitur sekaligus

```bash
python3 main.py --scan --scan-seconds 10 --track-connections --track-seconds 60
```

## Output Log Koneksi

Saat `--track-connections` aktif, script menambahkan baris log seperti:

```text
2026-03-27 10:15:42 - CONNECTED: AA:BB:CC:DD:EE:FF
2026-03-27 10:16:12 - DISCONNECTED: AA:BB:CC:DD:EE:FF
```

## Troubleshooting

- **`Command not found: bluetoothctl`**  
  Install paket BlueZ/tools sesuai distro Linux Anda.

- **`pyserial is not installed`**  
  Jalankan `python3 -m pip install pyserial`.

- **Tidak ada perangkat saat scan**  
  Pastikan adapter Bluetooth aktif dan izin akses sudah benar.

- **`--rssi` kosong/tidak ada output**  
  Adapter mungkin tidak tersedia, tidak ada perangkat di sekitar, atau `hcitool` tidak terpasang.

- **Gagal akses `/dev/ttyACM*`**  
  Cek port benar dan user punya permission ke perangkat serial (mis. grup `dialout`).

## Keamanan & Batasan

- Tool ini dibuat untuk **diagnostik lokal** dan observasi.
- Script tidak melakukan tindakan intrusif secara otomatis.
- Aktivasi fitur selalu eksplisit via flag CLI.

## Pengembangan Singkat

Menjalankan validasi cepat:

```bash
python3 -m py_compile main.py
python3 main.py --help
```

Jika ingin menambah fitur, pertahankan prinsip:

1. Flag eksplisit per fitur.
2. Error handling yang jelas untuk command eksternal.
3. Default yang aman dan tidak destruktif.
