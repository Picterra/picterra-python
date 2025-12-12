#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pprint import pprint

from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
# The Id of a folder/project you own
folder_id = "7ec40c11-f181-436a-9d33-d7b3f63e0e0f"
# Upload
local_raster_id = client.upload_raster("data/raster1.tif", name="A nice raster")
print("Uploaded local raster=", local_raster_id)
# Get the first batch of most recent images
first_page = client.list_rasters()
for raster in first_page:
    pprint("raster %s" % "\n".join(["%s=%s" % item for item in raster.items()]))
# Get the second batch
second_page = first_page.next()
# Get the first page applying a filter
for raster in client.list_rasters(folder_id):
    pprint("raster %s" % "\n".join(["%s=%s" % item for item in raster.items()]))
# Upload, edition and removal
local_raster_id = client.upload_raster("data/raster1.tif", name="A short-lived raster")
print("Uploaded a second local raster=", local_raster_id)
# Editing the image's band specification. See https://docs.picterra.ch/imagery/#Multispectral
client.edit_raster(
    local_raster_id,
    multispectral_band_specification={
        "ranges": [[0, 128], [0, 128], [0, 128]],
        "display_bands": [{"type": "multiband", "name": "default", "bands": [2, 1, 0]}],
    },
)
# Deleting the image
client.delete_raster(local_raster_id)
print("Deleted raster=", local_raster_id)
