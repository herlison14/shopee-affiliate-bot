"""
Hook PyInstaller para Anthropic SDK.
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files("anthropic")
hiddenimports = collect_submodules("anthropic")
