#!/usr/bin/env python3
"""
Deploy tags to devices in CloudVision using PyAVD workflows (CVAAS token).

Requirements:
    Python 3.12+
    pip install pyavd pandas openpyxl
    .xlsx file should be used 

How to run:
    source ~/cvp-env/bin/activate
    python3 tag_add.py
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
WORKSPACE_ID = f"tag_add_{uuid.uuid4().hex[:6]}"

# Disable TLS warnings for internal CVP environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# -------------------------------------------------------------------
# Tag Preparation Function
# -------------------------------------------------------------------
def create_tags(excel_file: str):
    """
    Read Excel and prepare tag + assignment lists.
    Required columns ideally are:
        Device, Device-ID, Campus, Campus-Pod, Access-Pod, Role 
    """
    logging.info(f"Reading Excel file: {excel_file}")
    df = pd.read_excel(excel_file, engine="openpyxl", header=0) # Start reading from second row
    print(df.columns.tolist())

    # Normalize and validate headers
    df.columns = df.columns.str.strip()
    expected = {"Device-ID", "Device", "MAC-Address", "Rack"} # Adjusted expected columns
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in Excel file: {missing}")

    device_tags = []
    tag_assignments = []

    # Find devices based on Device Name 
    for _, r in df.iterrows():
        device_id = str(r.get("Device-ID", "")).strip() 
        if not device_id:
            logging.warning(f"Skipping row with no Device: {r.to_dict()}")
            continue

        for label in ["Rack"]:
            value = r.get(label)
            if pd.isna(value) or not str(value).strip():
                continue  # skip empty or NaN tags

            value = str(value).strip()
            device_tags.append((label, value))
            tag_assignments.append((label, value, device_id, None))

    if not device_tags:
        logging.error("No valid tag values found. Please check Excel content.")
    else:
        logging.info(f"Prepared {len(device_tags)} tags and {len(tag_assignments)} tag assignments.")
        logging.info(f"Sample tag entries: {device_tags[:5]}")

    return device_tags, tag_assignments


# -------------------------------------------------------------------
# CVaaS Tag Deployment
# -------------------------------------------------------------------
async def deploy_tags(cloudvision: CloudVision, device_tags, tag_assignments):
    """
    Creates a workspace and deploys tags to CVaaS (without submitting).
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

            if not device_tags:
                logging.error("No tags to deploy — aborting.")
                return result

            logging.info("Deploying device tags...")
            await cv_client.set_tags(
                tags=device_tags,
                workspace_id=result.workspace.id,
                element_type="device",
            )

            logging.info("Assigning tags to devices...")
            await cv_client.set_tag_assignments(
                tag_assignments=tag_assignments,
                workspace_id=result.workspace.id,
                element_type="device",
            )

            # Do NOT submit workspace (per user instruction)
            logging.info("Workspace created and tags assigned (not submitted).")

            # Optional: review workspace via CVaaS web UI before submission

    except Exception as e:
        logging.error(f"Unexpected error during deployment: {e}")
        result.failed = True
        result.errors.append(e)

    return result


# -------------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------------
if __name__ == "__main__":
    logging.info("Starting CVAAS Tag Deployment Script")

    try:
        token = open(TOKEN_FILE, "r").read().strip()
        cloudvision = CVClient(servers=CVP_SERVER, token=token, verify_certs=False)

        device_tags, tag_assignments = create_tags(EXCEL_FILE)
        asyncio.run(deploy_tags(cloudvision, device_tags, tag_assignments))
        

        logging.info("✅ Tag deployment completed (workspace not submitted).")
    except Exception as e:
        logging.error(f"Script failed: {e}")
