# Device Tag Automation for CloudVision

Automate bulk device tagging on Arista CloudVision (CVaaS) using Python and PyAVD. Reads tag data from an Excel spreadsheet, creates a CVaaS workspace, and applies tag additions or removals — all without auto-submitting, so changes can be reviewed in the CVaaS UI before going live.

## Quick Start

```bash
# 1. Create virtual environment and install dependencies
python3 -m venv ~/cvp-env
source ~/cvp-env/bin/activate
pip install pyavd pandas openpyxl

# 2. Place your CVaaS service account token in cvp_token.txt

# 3. Prepare your Excel file (see format below)

# 4. Run
python3 tag_add.py              # Add tags
python3 tag_remove.py           # Remove tags
python3 tag_automation.py --add     # Combined script — add mode
python3 tag_automation.py --remove  # Combined script — remove mode
```

## How It Works

```
Excel (.xlsx)          Python Script          CVaaS
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│ Device-ID    │      │              │      │                  │
│ Device Name  │─────>│  Read Excel  │      │  Create          │
│ Rack Tag     │      │  Build Tags  │─────>│  Workspace       │
│ ...          │      │  Connect API │      │  Apply Tags      │
└──────────────┘      └──────────────┘      │  (Not Submitted) │
                                            └──────────────────┘
                                                     │
                                              Review in CVaaS UI
                                                     │
                                              Submit when ready
```

1. Reads device identifiers and tag values from an `.xlsx` file
2. Authenticates to CVaaS using a service account token
3. Creates a unique workspace per run (e.g., `tag_add_a1b2c3`)
4. Applies tag additions or removals within the workspace
5. Workspace remains **unsubmitted** — review changes in the CVaaS web UI before committing

## Excel Input Format

Create an `.xlsx` file with these columns (header row required):

| Device | Device-ID | MAC-Address | Rack |
|--------|-----------|-------------|------|
| SPINE-01 | ABC1234567 | aa:bb:cc:dd:ee:01 | Rack-A1 |
| LEAF-01 | DEF7654321 | aa:bb:cc:dd:ee:02 | Rack-B2 |

| Column | Required | Description |
|--------|----------|-------------|
| Device | Yes | Device hostname (for reference) |
| Device-ID | Yes | Serial number or device identifier in CVaaS |
| MAC-Address | No | Device MAC address (for reference) |
| Rack | Yes | Tag value to assign under the "Rack" label |

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `tag_add.py` | Add tags to devices | `python3 tag_add.py` |
| `tag_remove.py` | Remove tags from devices | `python3 tag_remove.py` |
| `tag_automation.py` | Combined add/remove in one script | `python3 tag_automation.py --add` or `--remove` |

All three scripts share the same configuration block and Excel format. Use `tag_automation.py` for a single entry point, or the individual scripts if you prefer separation.

## Configuration

Edit the variables at the top of any script:

```python
CVP_SERVER = "www.arista.io"      # CVaaS URL (or on-prem CVP IP/hostname)
TOKEN_FILE = "cvp_token.txt"      # Path to service account token file
EXCEL_FILE = "test.xlsx"          # Path to input spreadsheet
```

### Generating a CVaaS Token

1. Log in to your CVaaS instance
2. Navigate to **Settings** > **Service Accounts**
3. Create a service account or use an existing one
4. Generate a token and save it to `cvp_token.txt`

## Project Structure

```
device-tag-automation/
├── tag_add.py           # Tag addition script
├── tag_remove.py        # Tag removal script
├── tag_automation.py    # Combined add/remove script
├── cvp_token.txt        # Service account token (git-ignored)
├── test.xlsx            # Excel input file (git-ignored)
├── .gitignore
└── README.md
```

## Extending to Other Tags

The scripts currently tag devices with the **Rack** label. To add more tag labels (e.g., Campus, Role, Pod), update the loop in the tag preparation function:

```python
# Change this:
for label in ["Rack"]:

# To this:
for label in ["Rack", "Campus", "Role", "Pod"]:
```

Then add matching columns to your Excel file.

## Requirements

- Python 3.12+
- [pyavd](https://avd.arista.com/en/stable/docs/pyavd.html)
- [pandas](https://pandas.pydata.org/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- CVaaS service account token with tag management permissions
