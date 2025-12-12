"""
Demonstrate running a detector on all images within a project
"""

from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
# The Id of a folder/project you own
folder_id = "5cee6276-1c6b-4b00-9201-5d95f01b72b1"
detector_id = "afa558e7-e004-4c76-9aa6-8df72d33e568"


rasters = []
page = client.list_rasters(folder_id)
while True:
    rasters.extend(list(page))
    page = page.next()
    if page is None:
        break

print(f"Detecting on {len(rasters)} rasters")

operations = []
for raster in rasters:
    # Note that this will run and wait for results (so sequentially). You could
    # alternatively manually call the /detectors/<pk>/run/ endpoint for all rasters
    # and then have them run in parallel
    op = client.run_detector(detector_id, raster["id"])
    operations.append(op)
