#!/usr/bin/env python3
"""
Manage tags (add/remove) for devices in CloudVision using PyAVD workflows (CVAAS token).

Requirements:
    Python 3.12+
    pip install pyavd pandas openpyxl
    .xlsx file should be used

How to run:
    source ~/cvp-env/bin/activate
    python3 tag_automation.py --add      # To add tags
    python3 tag_automation.py --remove   # To remove tags
"""

import sys
import asyncio
import logging
import pandas as pd
import uuid
import urllib3
from pyavd._cv.client import CVClient
from pyavd._cv.workflows.create_workspace_on_cv import create_workspace_on_cv
from pyavd._cv.workflows.models import CVWorkspace, DeployToCvResult, CloudVision

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
CVP_SERVER = "www.arista.io"
TOKEN_FILE = "cvp_token.txt"
EXCEL_FILE = "test.xlsx"
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# -------------------------------------------------------------------
# Tag Preparation (Add)
# -------------------------------------------------------------------
def create_tags(excel_file: str):
    logging.info(f"Reading Excel file for tag addition: {excel_file}")
    df = pd.read_excel(excel_file, engine="openpyxl", header=0)
    df.columns = df.columns.str.strip()

    expected = {"Device-ID", "Device", "Rack"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in Excel file: {missing}")

    device_tags = []
    tag_assignments = []

    for _, r in df.iterrows():
        device_id = str(r.get("Device-ID", "")).strip()
        if not device_id:
            continue
        for label in ["Rack"]:
            value = r.get(label)
            if pd.isna(value) or not str(value).strip():
                continue
            value = str(value).strip()
            device_tags.append((label, value))
            tag_assignments.append((label, value, device_id, None))

    return device_tags, tag_assignments

# -------------------------------------------------------------------
# Tag Preparation (Remove)
# -------------------------------------------------------------------
def read_tags_to_remove(excel_file: str):
    logging.info(f"Reading Excel file for tag removal: {excel_file}")
    df = pd.read_excel(excel_file, engine="openpyxl", header=0)
    df.columns = df.columns.str.strip()

    expected = {"Device-ID", "Device", "Rack"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns in Excel file: {missing}")

    tag_removals = []
    for _, r in df.iterrows():
        device_id = str(r.get("Device-ID", "")).strip()
        if not device_id:
            continue
        for label in ["Rack"]:
            value = r.get(label)
            if pd.isna(value) or not str(value).strip():
                continue
            value = str(value).strip()
            tag_removals.append((label, value, device_id))
    return tag_removals

# -------------------------------------------------------------------
# CVaaS Deploy / Remove Functions
# -------------------------------------------------------------------
async def deploy_tags(cloudvision: CloudVision, device_tags, tag_assignments, workspace_id):
    result = DeployToCvResult(workspace=CVWorkspace(id=workspace_id))
    try:
        async with CVClient(
            servers=cloudvision._servers,
            token=cloudvision._token,
            verify_certs=False,
        ) as cv_client:

            await create_workspace_on_cv(workspace=result.workspace, cv_client=cv_client)

            if not device_tags:
                logging.error("No tags to deploy.")
                return result

            await cv_client.set_tags(
                tags=device_tags,
                workspace_id=result.workspace.id,
                element_type="device",
            )

            await cv_client.set_tag_assignments(
                tag_assignments=tag_assignments,
                workspace_id=result.workspace.id,
                element_type="device",
            )

            logging.info("Tag addition applied (workspace not submitted).")

    except Exception as e:
        logging.error(f"Error during deployment: {e}")
        result.failed = True
        result.errors.append(e)
    return result


async def remove_tags(cloudvision: CloudVision, tag_removals, workspace_id):
    result = DeployToCvResult(workspace=CVWorkspace(id=workspace_id))
    try:
        async with CVClient(
            servers=cloudvision._servers,
            token=cloudvision._token,
            verify_certs=False,
        ) as cv_client:

            await create_workspace_on_cv(workspace=result.workspace, cv_client=cv_client)

            if not tag_removals:
                logging.error("No tags to remove.")
                return result

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

            logging.info("Tag removals applied (workspace not submitted).")

    except Exception as e:
        logging.error(f"Error during tag removal: {e}")
        result.failed = True
        result.errors.append(e)
    return result

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("--add", "--remove"):
        logging.error("Usage: python3 tag_manage.py [--add | --remove]")
        sys.exit(1)

    mode = sys.argv[1]
    workspace_id = f"tag_{'add' if mode == '--add' else '--remove'}_{uuid.uuid4().hex[:6]}"

    try:
        token = open(TOKEN_FILE, "r").read().strip()
        cloudvision = CVClient(servers=CVP_SERVER, token=token, verify_certs=False)

        if mode == "--add":
            device_tags, tag_assignments = create_tags(EXCEL_FILE)
            asyncio.run(deploy_tags(cloudvision, device_tags, tag_assignments, workspace_id))
            logging.info("✅ Tag addition completed (workspace not submitted).")

        elif mode == "--remove":
            tag_removals = read_tags_to_remove(EXCEL_FILE)
            asyncio.run(remove_tags(cloudvision, tag_removals, workspace_id))
            logging.info("✅ Tag removal completed (workspace not submitted).")

    except Exception as e:
        logging.error(f"Script failed: {e}")
        sys.exit(1)
