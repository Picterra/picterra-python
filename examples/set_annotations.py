import json
from picterra import APIClient

client = APIClient(api_key='1234')
# Replace this with the id of one of your detectors
detector_id = '74576c1f-05d8-48cf-b515-9dba48edb6da'
# Replace this with the id of one of the training rasters for the detector above
raster_id = '8331b2a9-c7b1-439e-95e5-647e91abfb8f'

with open('data/outlines.geojson') as f:
    outlines = json.load(f)
client.set_annotations(detector_id, raster_id, 'outline', outlines)
