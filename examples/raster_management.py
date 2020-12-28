#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pprint import pprint
from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
# The Id of a folder/project you own
folder_id = "7ec40c11-f181-436a-9d33-d7b3f63e0e0f"

raster_id = client.upload_raster('data/raster1.tif', name='A nice raster')
print('Uploaded raster=', raster_id)

for raster in client.list_rasters():
    pprint('raster %s' % "\n".join(["%s=%s" % item for item in raster.items()]))

raster_id = client.upload_raster(
    'data/raster1.tif', name='Another nice raster in a nice folder',
    folder_id=folder_id, captured_at="2020-01-01T12:34:56.789Z"
)
print('Uploaded raster=', raster_id)

for raster in client.list_rasters(folder_id):
    pprint('raster %s' % "\n".join(["%s=%s" % item for item in raster.items()]))

client.delete_raster(raster_id)
print('Deleted raster=', raster_id)
