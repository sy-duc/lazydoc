# Hướng dẫn đóng gói và phát hành LazyDoc

Tài liệu này mô tả cách đóng gói LazyDoc thành ứng dụng Windows dễ cài đặt cho người dùng phổ thông.

## Chiến lược đề xuất

Luồng deploy khuyến nghị:

```text
Source code -> PyInstaller onedir -> Inno Setup installer -> phát hành file setup
```

Không nên bắt đầu bằng PyInstaller `onefile` vì LazyDoc dùng PySide6, AI SDK, xử lý Office/PDF và nhiều asset. `onedir` dễ debug hơn, ít lỗi runtime hơn và mở app nhanh hơn.

## Cấu trúc dữ liệu khi phát hành

Tách rõ thư mục cài đặt và dữ liệu người dùng:

```text
App install:
%LOCALAPPDATA%\Programs\LazyDoc

User data:
%LOCALAPPDATA%\LazyDoc
%LOCALAPPDATA%\LazyDoc\logs
```

Không lưu API key, database, log hoặc dữ liệu cá nhân trong thư mục cài đặt. Như vậy khi update app, dữ liệu người dùng vẫn được giữ nguyên.

## Chuẩn bị icon

Tạo file:

```text
src\assets\icons\app.ico
```

File `.ico` nên chứa nhiều kích thước:

```text
16x16
32x32
48x48
64x64
128x128
256x256
```

Icon cần được dùng ở 3 nơi:

1. Qt runtime: `QApplication.setWindowIcon(...)`.
2. PyInstaller: `--icon=src/assets/icons/app.ico`.
3. Inno Setup: `SetupIconFile=...`.

Trên Windows, nên set thêm AppUserModelID để taskbar không hiện icon Python.

## Build bằng PyInstaller

Cài dependency trong môi trường build:

```powershell
pip install -r requirements.txt
pip install pyinstaller
```

Build dạng `onedir`:

```powershell
pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name LazyDoc `
  --icon src\assets\icons\app.ico `
  src\main.py
```

Output dự kiến:

```text
dist\LazyDoc\LazyDoc.exe
```

Nếu dùng file `.spec`, hãy commit file spec riêng cho Windows build để quản lý asset, hidden imports và icon ổn định hơn.

## Asset cần kiểm tra trong bản build

Đảm bảo các asset sau có mặt trong bản `dist`:

```text
src\assets\i18n\vi.json
src\assets\i18n\en.json
src\assets\icons\*.svg
src\assets\icons\app.ico
config\config.yaml
```

Nếu PyInstaller không tự gom đủ, thêm vào `.spec` bằng `datas`.

## LibreOffice và file legacy

Các file `.doc` và `.ppt` cần LibreOffice headless để convert sang `.docx`/`.pptx`.

Bản phát hành đầu tiên không nên bundle LibreOffice vì installer sẽ rất nặng. Cách xử lý khuyến nghị:

- Hỗ trợ tốt `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.txt`, `.csv`, ảnh.
- Với `.doc`/`.ppt`, hiển thị thông báo yêu cầu cài LibreOffice hoặc chuyển file sang định dạng mới.

## Argos model offline

Nếu muốn dịch offline chạy ngay, cần bundle Argos models trong:

```text
resources\argos_models
```

Lưu ý: model có thể rất nặng. Nên có 2 hướng phát hành:

- Bản nhẹ: không bundle model, ưu tiên dịch AI.
- Bản full/offline: bundle model cần thiết.

## Tạo installer bằng Inno Setup

Khuyến nghị cài per-user để không cần quyền admin:

```ini
[Setup]
AppId={{PUT-STABLE-GUID-HERE}}
AppName=LazyDoc
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\LazyDoc
DefaultGroupName=LazyDoc
OutputDir=dist-installer
OutputBaseFilename=LazyDocSetup-0.1.0
SetupIconFile=src\assets\icons\app.ico
PrivilegesRequired=lowest
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\LazyDoc\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\LazyDoc"; Filename: "{app}\LazyDoc.exe"; IconFilename: "{app}\LazyDoc.exe"
Name: "{autodesktop}\LazyDoc"; Filename: "{app}\LazyDoc.exe"; IconFilename: "{app}\LazyDoc.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut ngoài Desktop"; GroupDescription: "Tùy chọn:"

[Run]
Filename: "{app}\LazyDoc.exe"; Description: "Mở LazyDoc"; Flags: nowait postinstall skipifsilent
```

`AppId` phải là GUID cố định và không đổi giữa các version.

## Update version mới

Không cần yêu cầu user xóa bản cũ.

Khi phát hành version mới:

1. Tăng `AppVersion`.
2. Tăng `OutputBaseFilename`.
3. Giữ nguyên `AppId`.
4. Build lại PyInstaller.
5. Build lại Inno Setup.
6. User chạy installer mới để upgrade đè.

Ví dụ:

```ini
AppVersion=0.2.0
OutputBaseFilename=LazyDocSetup-0.2.0
```

Nếu `AppId` giữ nguyên, Inno Setup sẽ nhận ra cài đặt cũ và update vào cùng thư mục.

User data vẫn giữ nguyên vì nằm ngoài `{app}`:

```text
%LOCALAPPDATA%\LazyDoc\lazydoc.db
%LOCALAPPDATA%\LazyDoc\logs
```

## Log chẩn đoán

LazyDoc ghi log tại:

```text
%LOCALAPPDATA%\LazyDoc\logs\lazydoc.log
```

Log dùng rotation để tránh phình ổ đĩa:

```text
lazydoc.log
lazydoc.log.1
lazydoc.log.2
lazydoc.log.3
```

Tổng dung lượng tối đa khoảng 8 MB.

Không log nội dung tài liệu, prompt đầy đủ, API key, text dịch hoặc raw response AI.

## Checklist test trước khi phát hành

Test trên máy Windows sạch, không có Python:

- Mở app từ Start Menu.
- Mở app từ Desktop shortcut nếu có.
- Icon taskbar không còn là icon Python.
- Cài đặt API key.
- Mở thư mục log từ Settings.
- Tổng hợp file `.txt`, `.docx`, `.xlsx`, `.pptx`, `.pdf`.
- Dịch mặc định.
- Dịch thông minh bằng AI.
- Output được lưu đúng thư mục.
- Đóng app, mở lại, provider/API key vẫn còn.
- Chạy installer version mới để upgrade, dữ liệu user không mất.
- Uninstall app, thư mục cài đặt được xóa.

## Gợi ý tự động hóa

Nên thêm script:

```text
scripts\build_windows.ps1
installer\lazydoc.iss
LazyDoc.spec
```

Mục tiêu là build release bằng một lệnh:

```powershell
.\scripts\build_windows.ps1
```

Output cuối cùng nên là:

```text
LazyDocSetup-<version>.exe
```
