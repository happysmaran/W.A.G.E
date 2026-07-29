import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'app/main.py',
    '--name=wage-backend',
    '--onedir',
    '--noconfirm',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    '--hidden-import=pydantic',
    '--hidden-import=sqlmodel',
    '--hidden-import=fastembed',
    '--hidden-import=trafilatura',
    '--hidden-import=playwright',
    '--hidden-import=beautifulsoup4',
    '--hidden-import=numpy',
    '--hidden-import=httpx',
    '--hidden-import=pydantic_settings',
    '--hidden-import=multipart',
    '--hidden-import=pypdf'
])
