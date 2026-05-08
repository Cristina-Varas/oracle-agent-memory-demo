import os
from pathlib import Path

import oci
from dotenv import load_dotenv

load_dotenv()
CONFIG_FILE = Path(os.getenv("OCI_CONFIG_FILE", "~/.oci/config")).expanduser()


config = oci.config.from_file(str(CONFIG_FILE), "DEFAULT")
oci.config.validate_config(config)

required_keys = ("user", "fingerprint", "tenancy", "region", "key_file")
missing_keys = [key for key in required_keys if not config.get(key)]
if missing_keys:
    raise ValueError(f"Missing OCI config keys: {', '.join(missing_keys)}")

key_file = Path(config["key_file"]).expanduser()
if not key_file.exists():
    raise FileNotFoundError(f"OCI key_file does not exist: {key_file}")

print("OCI config OK")
print(f"region={config['region']}")
print(f"key_file={key_file}")
