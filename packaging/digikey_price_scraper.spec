# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = []
hiddenimports += [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "cv2",
    "fitz",
    "pytesseract",
    "google.genai",
]

a = Analysis(
    ["../digikey_price_scraper.py"],
    pathex=[".."],
    binaries=[],
    datas=[
        # Bundle Pretendard / JetBrains Mono so the frozen build matches
        # the reference design (loaded at runtime via _fonts.load_fonts).
        ("../digikey_scraper/assets/fonts", "digikey_scraper/assets/fonts"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DigiKeyPriceScraper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DigiKeyPriceScraper",
)
