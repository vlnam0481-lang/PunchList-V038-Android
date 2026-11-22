# Punch List V38 — Android APK (Buildozer)

Đây là **dự án mã nguồn sẵn sàng cho quy trình tạo APK**, KHÔNG phải APK đã biên dịch.
Giữ nguyên logic nghiệp vụ V38 (thẻ lỗi, ảnh, PDF, JSON); chỉ bổ sung cầu nối
Android SAF để chọn ảnh và chọn nơi lưu PDF trong ứng dụng độc lập.

## Tạo APK bằng GitHub Actions (không cần máy Linux riêng)

1. Giải nén gói này, giữ các file và thư mục `.github` trong **thư mục gốc** của repo GitHub mới.
2. Tạo repository GitHub và tải toàn bộ nội dung lên branch `main` (đặc biệt: `.github/workflows/android-apk.yml`).
3. Trong GitHub, mở `Actions` → `Build Android APK - Punch List V38` → `Run workflow`.
4. Khi workflow **thành công**, mở lần chạy → `Artifacts` → `PunchList-V38-Android-debug-APK`.
5. Tải và giải nén artifact để nhận `*.apk`, chuyển sang Samsung Android và cài.
   Android có thể yêu cầu cho phép cài ứng dụng từ nguồn này.

**Nếu workflow thất bại**, xem `Build debug APK` trong Logs. Kivy, Pillow, ReportLab,
PyJNIus hoặc Android SDK/NDK có thể yêu cầu điều chỉnh phiên bản công cụ.
Chỉ artifact `.apk` do workflow biên dịch thành công mới có thể cài trực tiếp.

## Tạo APK bằng WSL2 / Ubuntu

Cài WSL2 Ubuntu bằng Windows, sử dụng thư mục nằm bên trong hệ tệp Linux.
Cần Python 3.12, Java 17 và các gói phụ trợ Buildozer.

```bash
sudo apt update
sudo apt install -y git zip unzip autoconf automake libtool pkg-config \
  zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev patchelf \
  python3-venv python3-pip openjdk-17-jdk
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel virtualenv
pip install 'buildozer>=1.5,<2' 'cython==0.29.34'
./build_android.sh
```

Sau khi thành công, file `.apk` được tạo trong `bin/`.

## Cách lưu dữ liệu trong APK

- JSON, ảnh đã chọn, ảnh thu nhỏ, PDF nội bộ: `self.user_data_dir/PunchList/`.
- Chọn ảnh: bộ chọn ảnh/tệp chuẩn Android, hỗ trợ chọn nhiều và lấy từ các thư mục.
- Lưu PDF: từ trang xem PDF bấm `Lưu…`, chọn thư mục và tên file trong Android Files.
- Không yêu cầu quyền truy cập toàn bộ bộ nhớ vì dùng Storage Access Framework.
- Dữ liệu của Pydroid 3 **không tự chuyển sang APK**, do APK sử dụng vùng lưu riêng.
  Sao chép thư mục/hồ sơ từ Pydroid 3 cần một bước nhập dữ liệu riêng.

## Ghi chú kỹ thuật

- target SDK 35, min SDK 24, arm64-v8a; đóng gói debug để cài thử.
- Bundle gồm `main.py`, `pdf_form_v2.py`, `android_files.py` và font Unicode.
- Nhấn giữ ảnh để xóa, kiểm soát danh sách công tác, PDF 40/60 và mẫu hành chính giữ nguyên.
- **Không xác nhận APK chạy được trên Samsung** cho đến khi build và kiểm thử trên thiết bị.
- Nếu yêu cầu phân phối ngoài môi trường thử nghiệm, cần ký bản release bằng keystore riêng.
