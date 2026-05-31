from dataclasses import dataclass

import yaml


@dataclass
class AppConfig:
    claim_template_path:str
    calculation_claim_template_path:str
    save_data_folder: str
    point_overdue_keywords:dict
    point_overdue_excluded:list
    service_type_keywords:dict
    service_type_excluded:list | None
    debug_mode: bool


def save_yaml_config(filename: str, config: dict):
    """Save configuration to YAML file"""
    with open(filename, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def load_yaml_config(filename: str) -> AppConfig:
    """Load configuration from YAML file and return as YamlConfig instance"""
    with open(filename) as f:
        config_data = yaml.safe_load(f)

    return AppConfig(
        save_data_folder=config_data["save_data_folder"],
        debug_mode=config_data["debug"],
        claim_template_path=config_data['claim_template_path'],
        calculation_claim_template_path=config_data['calculation_claim_template_path'],
        point_overdue_keywords=config_data['point_overdue_key_words_list_weighted'],
        point_overdue_excluded=config_data['point_overdue_key_words_excluded'],
        service_type_keywords = config_data['service_type_key_words_list_weighted'],
        service_type_excluded = None
    )
