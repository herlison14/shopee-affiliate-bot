"""
Hook PyInstaller para Playwright — inclui os drivers necessários.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("playwright")
hiddenimports = collect_submodules("playwright")
