# Python Tagging — CloudVision Device Tag Automation

Bulk add and remove device tags on Arista CloudVision (CVaaS) using PyAVD workflows. Tags are read from an Excel spreadsheet and deployed via workspace (not auto-submitted).

## Quick Start

```bash
# Setup
python3 -m venv ~/cvp-env
source ~/cvp-env/bin/activate
pip install pyavd pandas openpyxl

# Add tags from Excel
python3 tag_add.py

# Remove tags from Excel
python3 tag_remove.py

# Combined script (add or remove)
python3 tag_automation.py --add
python3 tag_automation.py --remove
```

## Files

| File | Description |
|------|-------------|
| `tag_add.py` | Add device tags to CVaaS from Excel |
| `tag_remove.py` | Remove device tags from CVaaS using Excel |
| `tag_automation.py` | Combined add/remove script (`--add` or `--remove`) |
| `cvp_token.txt` | CVaaS service account token (not committed) |
| `test.xlsx` | Excel input with device/tag data (not committed) |

## Excel Format

The input `.xlsx` file should have these columns:

| Device | Device-ID | MAC-Address | Rack |
|--------|-----------|-------------|------|
| switch-01 | ABC123... | aa:bb:cc:... | Rack-A1 |

- **Device** — device hostname
- **Device-ID** — serial number or device identifier in CVaaS
- **Rack** — tag value to assign (tag label is "Rack")

## How It Works

1. Reads device and tag data from Excel
2. Connects to CVaaS using a service account token
3. Creates a workspace (unique ID per run)
4. Adds or removes tag assignments in the workspace
5. Workspace is **not submitted** — review in CVaaS UI before submitting

## Configuration

Edit the top of any script to change:

```python
CVP_SERVER = "www.arista.io"      # CVaaS or on-prem CVP URL
TOKEN_FILE = "cvp_token.txt"      # Path to service account token
EXCEL_FILE = "test.xlsx"          # Input spreadsheet
```

## Requirements

- Python 3.12+
- pyavd
- pandas
- openpyxl
