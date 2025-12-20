import yaml
import os

class ConfigLoader:
    @staticmethod
    def load_config(config_path):
        """
        Loads and validates a YAML configuration file.
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Basic validation
        required_fields = ['channel_id', 'type', 'language']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in config: {config_path}")
        
        return config

if __name__ == "__main__":
    # Test loading
    try:
        loader = ConfigLoader()
        # print(loader.load_config("automation/config/nepali_news.yaml"))
    except Exception as e:
        print(f"Error: {e}")
