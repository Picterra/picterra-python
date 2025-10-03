####
# This example utilises only the Picterra API with HTTP calls and does not rely on the api client
#
# It creates a new plots group, uploads a geojson file to create some plots and then executes an
# analysis precheck to diagnose whether the geojson file conforms to the rules for this methodology.
#
###
import datetime
import json
import os
import time
import urllib.request

import requests

####
# INPUT variables
#
# You should change these to supply your own details
####
PICTERRA_API_KEY = "PUT-YOUR-KEY-HERE"
METHODOLOGY_NAME = "coffee"
PLOTS_GROUP_NAME = "My plots group"
# You can specify multiple files in this list, they will be combined into a single plots group
FILES_TO_UPLOAD = ["plots.geojson"]
# The beginning of the analysis period in this example is always the EUDR cut-off date 2020-12-31
# ANALYSIS_DATE is the end of the analysis period, we set to today's date by default
ANALYSIS_DATE = datetime.date.today().isoformat()
####
# END INPUT variables
#
# Variables below here will not usually need to be changed
####


####
# CONSTANTS
#
# Other global constants used through the script, you should not need to change these
####
ROOT_URL = "https://app.picterra.ch/public/api/plots_analysis/v1"
AUTH_HEADERS = { "x-api-key": PICTERRA_API_KEY }

####
# Helper functions
#
# These functions carry out tasks which are common to multiple endpoints across the Picterra API
# such as polling for status on long-running operations
####
def wait_for_operation_to_complete(poll_details):
    current_status = "running"
    while current_status not in ('failed', 'success'):
        resp = requests.get(f"{ROOT_URL}/operations/{poll_details['operation_id']}/", headers=AUTH_HEADERS)
        resp.raise_for_status()
        current_status = resp.json()["status"]
        time.sleep(poll_details["poll_interval"])
    assert current_status == "success", "Operation failed: " + resp.json()["errors"]["message"]
    return resp.json()


def get_from_api(endpoint: str):
    resp = requests.get(f"{ROOT_URL}{endpoint}", headers=AUTH_HEADERS)
    resp.raise_for_status()
    return resp.json()

def post_to_api(endpoint: str, data: dict):
    resp = requests.post(f"{ROOT_URL}{endpoint}", json=data, headers=AUTH_HEADERS)
    resp.raise_for_status()
    return resp.json()

####
# Main Script
#
# From here, the script executes several steps:
#
# 1. Find the methodology ID for the methodology name provided in the input variables
# 2. Create a new plots group with the plots group name provided in the input variables
# 3. Upload the provided plot geometries files and ingest them to the plots group
# 4. Retrieve the ingested plots group in geojson format and generate a list of plot ids from it
# 5. Run an analysis precheck for the generated list of plot ids (from step 4) and report on the
#    conformity with methodology rules
####

# Fetch the methodologies to find the ID for our chosen methodology name
# (defined in the INPUT variables section above)
print(f"Listing methodologies and finding methodology ID for {METHODOLOGY_NAME}...")
results = get_from_api(f"/methodologies/?search={METHODOLOGY_NAME}")["results"]
assert len(results) == 1, f"Cannot determine methodology ID when searching for {METHODOLOGY_NAME}"
methodology_id = results[0]["id"]


# Create a plots group for the given methodology
print("Creating plotsgroup...")
poll_details = post_to_api(f"/plots_groups/", data={
    "name": PLOTS_GROUP_NAME,
    "methodology_id": methodology_id
})
completed_operation_response = wait_for_operation_to_complete(poll_details)
plots_group_id = completed_operation_response["results"]["plots_group_id"]

# Upload and commit plots data
print("Uploading plots...")
files = []

# Generate an upload ID and URL and upload each file
for filename in FILES_TO_UPLOAD:
  resp = post_to_api("/upload/file/", data={})
  upload_id = resp["upload_id"]
  upload_url = resp["upload_url"]
  with open(filename, "rb") as fh:
    resp = requests.put(upload_url, data=fh.read())
    files.append({"filename": os.path.basename(filename), "upload_id": upload_id})

# Start the operation to parse and merge the plots (set overwrite to True to replace all
# existing plots)
poll_details = post_to_api(
    f"/plots_groups/{plots_group_id}/upload/commit/",
    data={"files": files, "overwrite": False}
)
wait_for_operation_to_complete(poll_details)

# Export the plots group to retrieve the plot ids
print("Exporting plot ids...")
poll_details = post_to_api(f"/plots_groups/{plots_group_id}/export/", data={"format": "geojson"})
completed_operation_response = wait_for_operation_to_complete(poll_details)
download_url = completed_operation_response["results"]["download_url"]
# Download the results file
urllib.request.urlretrieve(download_url, "export.geojson")
# Extract plot ids from that file
with open("export.geojson", "r") as f:
    plots = json.load(f)
plot_ids = { "plot_ids": [p["properties"]["plot_id"] for p in plots["features"]] }
with open("plot_ids.json", "w") as f:
    json.dump(plot_ids, f)

# Precheck to check conformity
print(f"Analysis precheck...")
## Upload the file containing the ids of plots to analyse
upload = post_to_api("/upload/file/", data={})
with open("plot_ids.json") as f:  # a JSON file as an object with one "plot_ids" array
    data = json.load(f)
requests.put(upload["upload_url"], json=data)

# Precheck the plots to get whether they conform to the methodology rules
poll_details = post_to_api(f"/plots_groups/{plots_group_id}/analysis/precheck/", data={
    "analysis_name": "Shipment 1234",
    "date_from": "2020-12-31", # EUDR cutoff date
    "date_to": ANALYSIS_DATE,
    "upload_id": upload["upload_id"]
})
completed_operation_response = wait_for_operation_to_complete(poll_details)
precheck_result_url = completed_operation_response["results"]["precheck_data_url"]
resp = requests.get(precheck_result_url)
resp.raise_for_status()
precheck_result = resp.json()['status']
assert precheck_result in ["passed", "failed"], f"Unable to determine conformity from unknown precheck result {precheck_result}"
conform = False
if precheck_result == "passed":
    conform = True

if conform:
    print("Plots group conforms and is ready for analysis")
else:
    print("Plots group has diagnostics which need addressing before analysis")
