####
# This example utilises only the Picterra API with HTTP calls and does not rely on the api client
#
# It takes an existing plots group ID and runs an analysis across the entire plot group (all plots)
# Once the analysis is complete, it downloads the detailed analysis report and uses the provided
# statistics to determine the maximum deforestation risk level of all plots and flags whether to
# continue with EUDR DDS submission or not
#
###
import json
import urllib.request
import datetime
import time
import requests

####
# INPUT variables
#
# You should change these to supply your own details
####
PICTERRA_API_KEY = "PUT-YOUR-KEY-HERE"
PLOTS_GROUP_ID = "PUT-YOUR-PLOTSGROUP-ID-HERE"
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
AUTH_HEADERS = {"x-api-key": PICTERRA_API_KEY}


####
# Helper functions
#
# These functions carry out tasks which are common to multiple endpoints across the Picterra API
# such as polling for status on long-running operations
####
def wait_for_operation_to_complete(poll_details):
    current_status = "running"
    while current_status not in ("failed", "success"):
        resp = requests.get(
            f"{ROOT_URL}/operations/{poll_details['operation_id']}/",
            headers=AUTH_HEADERS,
        )
        resp.raise_for_status()
        current_status = resp.json()["status"]
        time.sleep(poll_details["poll_interval"])
    assert current_status == "success", (
        "Operation failed: " + resp.json()["errors"]["message"]
    )
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
# 1. Get the full list of plot ids for the plotsgroup
# 2. Run the analysis for those plot ids
# 3. Retrieve the analysis report in geojson format
# 4. Iterate through the results and track the highest risk, reporting back whether the plot group
#    is in the high risk category or not
####

# Export the plots group to retrieve the plot ids
print("Exporting plot ids...")
poll_details = post_to_api(
    f"/plots_groups/{PLOTS_GROUP_ID}/export/", data={"format": "geojson"}
)
completed_operation_response = wait_for_operation_to_complete(poll_details)
download_url = completed_operation_response["results"]["download_url"]
# Download the results file
urllib.request.urlretrieve(download_url, "export.geojson")
# Extract plot ids from that file
with open("export.geojson", "r") as f:
    plots = json.load(f)
plot_ids = {"plot_ids": [p["properties"]["plot_id"] for p in plots["features"]]}
with open("plot_ids.json", "w") as f:
    json.dump(plot_ids, f)

# Upload the list of plots and start the analysis
print(f"Starting analysis...")
## Upload the file containing the ids of plots to analyse
upload = post_to_api("/upload/file/", data={})
with open("plot_ids.json") as f:  # a JSON file as an object with one "plot_ids" array
    data = json.load(f)
requests.put(upload["upload_url"], json=data)

# Precheck the plots to get whether they conform to the methodology rules
poll_details = post_to_api(
    f"/plots_groups/{PLOTS_GROUP_ID}/analysis/",
    data={
        "analysis_name": "Shipment 1234",
        "date_from": "2020-12-31",  # EUDR cutoff date
        "date_to": ANALYSIS_DATE,
        "upload_id": upload["upload_id"],
    },
)
completed_operation_response = wait_for_operation_to_complete(poll_details)
analysis_id = completed_operation_response["results"]["analysis_id"]

analysis_detail = get_from_api(
    f"/plots_groups/{PLOTS_GROUP_ID}/analysis/{analysis_id}/"
)
print(f"Analysis done. Browse url:\n{analysis_detail['url']}")

# List reports and get the eudr_global report
print("Listing reports...")
report_list = get_from_api(
    f"/plots_groups/{PLOTS_GROUP_ID}/analysis/{analysis_id}/reports/"
)
report_id = None
for result in report_list["results"]:
    print(f"{result['name']}\t{result['report_type']}\t{result['id']}")
    if result["report_type"] == "eudr_global":
        report_id = result["id"]

# Download the report's details
# Get report details including download URLs
report = get_from_api(
    f"/plots_groups/{PLOTS_GROUP_ID}/analysis/{analysis_id}/reports/{report_id}/"
)
print(f"Downloading geojson format report")
for artifact in report["artifacts"]:
    # only download the geojson report
    if artifact["filename"] == "analysis_details.json":
        urllib.request.urlretrieve(artifact["download_url"], artifact["filename"])
print(f"Processing report to assess overall risk")
high_risk = False
with open("analysis_details.json", "r") as f:
    analysis = json.load(f)
    results = {}
    for section in analysis["aggregate_stats"]["sections"]:
        if section["title"] == "Deforestation":
            for datum in section["data"]:
                results[datum["name"]] = results[datum["value"]]
    if results["High"] > 0:
        print("Overall risk is High")
        high_risk = True
    elif results["Low"] > 0:
        print("Overall risk is Low")
    else:
        print("Overall risk is Very low")

if high_risk:
    print("Take some action here to alert / stop shipment")
else:
    print("Proceed to submit EUDR DDS")
