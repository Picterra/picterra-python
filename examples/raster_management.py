#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pprint import pprint

from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
# The Id of a folder/project you own
folder_id = "7ec40c11-f181-436a-9d33-d7b3f63e0e0f"

local_raster_id = client.upload_raster('data/raster1.tif', name='A nice raster')
print('Uploaded local raster=', local_raster_id)

for raster in client.list_rasters():
    pprint('raster %s' % "\n".join(["%s=%s" % item for item in raster.items()]))

for raster in client.list_rasters(folder_id):
    pprint('raster %s' % "\n".join(["%s=%s" % item for item in raster.items()]))

local_raster_id = client.upload_raster('data/raster1.tif', name='A short-lived raster')
print('Uploaded a second local raster=', local_raster_id)
client.delete_raster(local_raster_id)
print('Deleted raster=', local_raster_id)
