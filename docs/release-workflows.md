# Quy trình deploy và phát hành LazyDoc

Tài liệu này mô tả ba quy trình:

1. Developer build bộ cài LazyDoc.
2. Người dùng cài đặt hoặc nâng cấp LazyDoc.
3. Developer phát hành một phiên bản mới.

## Tổng quan

```text
Source code
    -> PyInstaller onedir
    -> dist\LazyDoc\
    -> Inno Setup
    -> LazyDocSetup-x.y.z.exe
    -> GitHub Release
    -> Người dùng tải và cài đặt
```

PyInstaller tạo ứng dụng dạng `onedir`. Inno Setup đóng gói toàn bộ thư mục
`onedir` thành một file cài đặt `.exe` duy nhất để phân phối.

## 1. Quy trình deploy

Quy trình này dành cho developer tạo file cài đặt trên máy Windows.

### Bước 1: Chuẩn bị môi trường

Yêu cầu:

- Windows 10 hoặc mới hơn.
- Python và virtual environment của dự án.
- Inno Setup.
- Source code tại đúng phiên bản cần phát hành.

Cài dependency:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
```

### Bước 2: Chuẩn bị tài nguyên

Kiểm tra các tài nguyên cần đóng gói:

```text
config\config.yaml
src\assets\i18n
src\assets\icons
favicon.ico
resources\argos_models
```

`resources\argos_models` chỉ bắt buộc đối với bản Full Offline. Bản Lite có
thể không chứa model và sẽ cần mạng để tải model khi sử dụng lần đầu.

Không đưa API key, database, log hoặc dữ liệu người dùng vào bộ cài.

### Bước 3: Build PyInstaller dạng onedir

Khuyến nghị quản lý cấu hình build bằng file `LazyDoc.spec`. Nếu chưa có file
spec, có thể build thử bằng lệnh:

```powershell
pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name LazyDoc `
  --icon favicon.ico `
  --add-data "config\config.yaml;config" `
  --add-data "src\assets;src\assets" `
  --add-data "favicon.ico;." `
  --add-data "resources\argos_models;resources\argos_models" `
  src\main.py
```

Kết quả:

```text
dist\LazyDoc\LazyDoc.exe
```

Với bản Lite, bỏ dòng `--add-data` dành cho `resources\argos_models`.

### Bước 4: Kiểm tra bản onedir

Chạy trực tiếp:

```powershell
dist\LazyDoc\LazyDoc.exe
```

Kiểm tra tối thiểu:

- Ứng dụng khởi động được.
- Icon, file ngôn ngữ và config được load.
- Có thể mở và xử lý các định dạng tài liệu hỗ trợ.
- Dịch AI hoạt động khi đã cấu hình API key.
- Dịch offline hoạt động trong bản Full Offline.
- Log và database được ghi vào `%LOCALAPPDATA%\LazyDoc`, không ghi vào
  `dist\LazyDoc`.

### Bước 5: Tạo bộ cài bằng Inno Setup

File Inno Setup cần giữ `AppId` cố định giữa mọi phiên bản:

```ini
#define MyAppVersion "1.0.0"

[Setup]
AppId={{PUT-STABLE-GUID-HERE}}
AppName=LazyDoc
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\LazyDoc
DefaultGroupName=LazyDoc
OutputDir=dist-installer
OutputBaseFilename=LazyDocSetup-{#MyAppVersion}
SetupIconFile=favicon.ico
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\LazyDoc\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài Desktop"; GroupDescription: "Tùy chọn:"

[Icons]
Name: "{autoprograms}\LazyDoc"; Filename: "{app}\LazyDoc.exe"
Name: "{autodesktop}\LazyDoc"; Filename: "{app}\LazyDoc.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LazyDoc.exe"; Description: "Mở LazyDoc"; Flags: nowait postinstall skipifsilent
```

Compile bằng Inno Setup Compiler hoặc command line:

```powershell
ISCC.exe installer\lazydoc.iss
```

Kết quả cuối cùng:

```text
dist-installer\LazyDocSetup-1.0.0.exe
```

### Bước 6: Kiểm tra bộ cài

Nên kiểm tra trên một máy Windows sạch, không cài Python:

- Cài đặt không cần quyền administrator.
- Mở app từ Start Menu và Desktop shortcut.
- Các chức năng chính hoạt động.
- Đóng và mở lại app không mất cấu hình.
- Uninstall xóa thư mục ứng dụng.
- Dữ liệu người dùng được xử lý theo chính sách của sản phẩm.

## 2. Quy trình dành cho người dùng

### Cài đặt lần đầu

1. Mở trang GitHub Releases chính thức của LazyDoc.
2. Chọn phiên bản mới nhất.
3. Tải `LazyDocSetup-x.y.z.exe`.
4. Kiểm tra đúng tên nhà phát hành hoặc checksum nếu release có cung cấp.
5. Chạy file setup và làm theo hướng dẫn.
6. Mở LazyDoc từ Start Menu hoặc Desktop.
7. Cấu hình API key nếu sử dụng tính năng AI.

Người dùng không cần cài Python và không cần tải thư mục `onedir`.

### Nâng cấp phiên bản

1. Tải `LazyDocSetup-x.y.z.exe` của phiên bản mới.
2. Đóng LazyDoc nếu ứng dụng đang chạy.
3. Chạy installer mới.
4. Installer nhận diện phiên bản cũ và cài đè vào cùng thư mục.
5. Mở lại LazyDoc và kiểm tra phiên bản.

Không cần uninstall phiên bản cũ trước khi nâng cấp.

Dữ liệu người dùng phải được lưu ngoài thư mục cài đặt:

```text
Ứng dụng:
%LOCALAPPDATA%\Programs\LazyDoc

Dữ liệu người dùng:
%LOCALAPPDATA%\LazyDoc
```

Nhờ vậy database, API key đã mã hóa, log và model Argos đã cài không bị thay
thế khi nâng cấp ứng dụng.

## 3. Quy trình phát hành phiên bản mới

Quy trình này áp dụng mỗi khi phát hành một version mới, ví dụ `1.2.0`.

### Bước 1: Chuẩn bị release

1. Chốt phạm vi thay đổi.
2. Chạy test tự động.
3. Kiểm tra thủ công các luồng chính.
4. Cập nhật version thành `1.2.0` tại các vị trí sử dụng version.
5. Cập nhật changelog hoặc release notes.

Sử dụng semantic versioning:

```text
MAJOR.MINOR.PATCH

1.0.1: sửa lỗi, không thay đổi lớn về tính năng
1.1.0: thêm tính năng tương thích ngược
2.0.0: có thay đổi không tương thích
```

### Bước 2: Tạo bộ cài mới

1. Xóa output build cũ bằng quy trình build của dự án.
2. Build lại PyInstaller `onedir`.
3. Kiểm tra `dist\LazyDoc\LazyDoc.exe`.
4. Đổi `MyAppVersion` trong Inno Setup thành `1.2.0`.
5. Giữ nguyên `AppId`.
6. Compile để tạo:

```text
dist-installer\LazyDocSetup-1.2.0.exe
```

### Bước 3: Kiểm tra nâng cấp

Trên máy test:

1. Cài phiên bản trước, ví dụ `1.1.0`.
2. Tạo dữ liệu thử và lưu cấu hình.
3. Chạy `LazyDocSetup-1.2.0.exe`.
4. Xác nhận ứng dụng được nâng cấp tại chỗ.
5. Xác nhận dữ liệu và cấu hình cũ vẫn còn.
6. Kiểm tra đầy đủ các chức năng chính.

### Bước 4: Tạo checksum

Tạo SHA-256 cho installer:

```powershell
Get-FileHash .\dist-installer\LazyDocSetup-1.2.0.exe -Algorithm SHA256
```

Lưu checksum vào release notes để người dùng hoặc auto-updater có thể xác
minh file tải về.

### Bước 5: Phát hành trên GitHub Releases

1. Push source code và tag phiên bản:

```powershell
git tag v1.2.0
git push origin v1.2.0
```

2. Tạo GitHub Release từ tag `v1.2.0`.
3. Ghi release notes: tính năng mới, lỗi đã sửa và lưu ý nâng cấp.
4. Upload `LazyDocSetup-1.2.0.exe`.
5. Công bố release.

URL tải dự kiến:

```text
https://github.com/<owner>/<repo>/releases/download/v1.2.0/LazyDocSetup-1.2.0.exe
```

### Bước 6: Cập nhật thông tin auto-update

Nếu LazyDoc có auto-update, cập nhật manifest tại một URL cố định:

```json
{
  "version": "1.2.0",
  "download_url": "https://github.com/<owner>/<repo>/releases/download/v1.2.0/LazyDocSetup-1.2.0.exe",
  "sha256": "<SHA-256-CUA-FILE-INSTALLER>",
  "release_notes_url": "https://github.com/<owner>/<repo>/releases/tag/v1.2.0"
}
```

Thứ tự an toàn:

1. Upload installer và công bố GitHub Release.
2. Kiểm tra URL tải hoạt động.
3. Cập nhật manifest auto-update sau cùng.

Không cập nhật manifest trước khi installer sẵn sàng, vì app cũ có thể phát
hiện phiên bản mới nhưng không tải được file.

## Checklist phát hành nhanh

- [ ] Test tự động thành công.
- [ ] Version và release notes đã cập nhật.
- [ ] PyInstaller `onedir` build thành công.
- [ ] Tài nguyên và model cần thiết đã được bundle.
- [ ] Bản `onedir` chạy trên máy sạch.
- [ ] Inno Setup dùng đúng version và giữ nguyên `AppId`.
- [ ] Installer cài mới thành công.
- [ ] Installer nâng cấp từ bản cũ mà không mất dữ liệu.
- [ ] SHA-256 đã được tạo.
- [ ] Git tag và GitHub Release đã được tạo.
- [ ] Installer đã được upload và tải thử thành công.
- [ ] Manifest auto-update đã được cập nhật sau cùng.
