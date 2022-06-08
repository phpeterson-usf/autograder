from pathlib import Path

config_root = Path.home() / '.config' / 'grade'

def config_path():
    config_path =  config_root / 'config.toml'
    return config_path

def config_temp_path():
    temp_path = config_root / 'temp.toml'
    return temp_path
