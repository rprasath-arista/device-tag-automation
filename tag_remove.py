#!/usr/bin/env python3
"""
Remove tags from devices in CloudVision using PyAVD workflows (CVAAS token).

Requirements:
    Python 3.12+
    pip install pyavd pandas openpyxl
    .xlsx file should be used 

How to run:
    source ~/cvp-env/bin/activate
    python3 tag_remove.py
"""

import asyncio
import logging
import pandas as pd
import uuid
import urllib3
from pyavd._cv.client import CVClient
from pyavd._cv.workflows.create_workspace_on_cv import create_workspace_on_cv
from pyavd._cv.workflows.finalize_workspace_on_cv import finalize_workspace_on_cv
from pyavd._cv.workflows.models import CVWorkspace, DeployToCvResult, CloudVision

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
CVP_SERVER = "www.arista.io"
TOKEN_FILE = "cvp_token.txt"
EXCEL_FILE = "test.xlsx"
WORKSPACE_ID = f"tag_remove_{uuid.uuid4().hex[:6]}"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# -------------------------------------------------------------------
# Tag Removal Preparation
# -------------------------------------------------------------------
def read_tags_to_remove(excel_file: str):
    """
    Read Excel and prepare tag removal targets.
    Required columns ideally are:
        Device, Device-ID, Rack
    """
    logging.info(f"Reading Excel file: {excel_file}")
    df = pd.read_excel(excel_file, engine="openpyxl", header=0)
    print(df.columns.tolist())

    df.columns = df.columns.str.strip()
    expected = {"Device-ID", "Device", "Rack"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in Excel file: {missing}")

    tag_removals = []

    for _, r in df.iterrows():
        device_id = str(r.get("Device-ID", "")).strip()
        if not device_id:
            logging.warning(f"Skipping row with no Device-ID: {r.to_dict()}")
            continue

        for label in ["Rack"]:
            value = r.get(label)
            if pd.isna(value) or not str(value).strip():
                continue
            value = str(value).strip()
            tag_removals.append((label, value, device_id))

    if not tag_removals:
        logging.error("No valid tag removals found. Please check Excel content.")
    else:
        logging.info(f"Prepared {len(tag_removals)} tag removals.")
        logging.info(f"Sample tag removal entries: {tag_removals[:5]}")

    return tag_removals

# -------------------------------------------------------------------
# CVaaS Tag Removal
# -------------------------------------------------------------------
async def remove_tags(cloudvision: CloudVision, tag_removals):
    """
    Creates a workspace and removes tags from CVaaS devices (without submitting).
    """
    result = DeployToCvResult(workspace=CVWorkspace(id=WORKSPACE_ID))

    try:
        async with CVClient(
            servers=cloudvision._servers,
            token=cloudvision._token,
            verify_certs=False,
        ) as cv_client:

            logging.info(f"Creating workspace: {WORKSPACE_ID}")
            await create_workspace_on_cv(workspace=result.workspace, cv_client=cv_client)

            if not tag_removals:
                logging.error("No tags to remove — aborting.")
                return result

            logging.info("Removing tags from devices...")
            for label, value, device_id in tag_removals:
                try:
                    await cv_client.delete_tag_assignments(
                        tag_assignments=[(label, value, device_id, None)],
                        workspace_id=result.workspace.id,
                        element_type="device",
                    )
                    logging.info(f"Removed tag {label}:{value} from {device_id}")
                except Exception as e:
                    logging.error(f"Failed to remove tag {label}:{value} from {device_id}: {e}")

            logging.info("Workspace created and tag removals applied (not submitted).")

    except Exception as e:
        logging.error(f"Unexpected error during tag removal: {e}")
        result.failed = True
        result.errors.append(e)

    return result

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    logging.info("Starting CVAAS Tag Removal Script")

    try:
        token = open(TOKEN_FILE, "r").read().strip()
        cloudvision = CVClient(servers=CVP_SERVER, token=token, verify_certs=False)

        tag_removals = read_tags_to_remove(EXCEL_FILE)
        asyncio.run(remove_tags(cloudvision, tag_removals))

        logging.info("✅ Tag removal completed (workspace not submitted).")
    except Exception as e:
        logging.error(f"Script failed: {e}")
