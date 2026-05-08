import os
from pathlib import Path

import oci


CONFIG_FILE = Path(os.getenv("OCI_CONFIG_FILE", "~/.oci/config")).expanduser()

config = oci.config.from_file(str(CONFIG_FILE), "DEFAULT")
identity = oci.identity.IdentityClient(config)

tenancy_id = config["tenancy"]
compartments = identity.list_compartments(
    tenancy_id,
    compartment_id_in_subtree=True,
    access_level="ACCESSIBLE",
).data

print("Compartments visible to this OCI user:")
print(f"- tenancy-root: {tenancy_id}")
for compartment in compartments:
    print(f"- {compartment.name}: {compartment.id}")
