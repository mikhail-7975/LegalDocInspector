import yaml
from dataclasses import dataclass


@dataclass
class AppConfig:
    save_data_folder: str
    debug_mode: bool


def save_yaml_config(filename: str, config: dict):
    """Save configuration to YAML file"""
    with open(filename, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def load_yaml_config(filename: str) -> AppConfig:
    """Load configuration from YAML file and return as YamlConfig instance"""
    with open(filename, "r") as f:
        config_data = yaml.safe_load(f)

    return AppConfig(
        database_host=config_data["database"]["host"],
        database_port=config_data["database"]["port"],
        debug_mode=config_data["debug_mode"],
        allowed_users=config_data["allowed_users"],
    )
