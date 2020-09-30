import json
from picterra import APIClient

# Put your API key either:
# * replacing '1234'
# * not putting arguments to APIClient but setting the PICTERRA_API_KEY environment variable 
client = APIClient(api_key='59c4715cee86d854e233739260fdfd8373f13fc393ee66ca389b04bc40e80472', base_url='https://app-testing.picterra.ch/public/api/v1/')


detector_id = client.create_detector('My first detector')
# Training raster for the detector above
raster_id = client.upload_raster('data/raster1.tif', name='a nice raster')
client.add_raster_to_detector(raster_id, detector_id)
# Add annotations
with open('data/outline.geojson') as f:
    outlines = json.load(f)
client.set_annotations(detector_id, raster_id, 'outline', outlines)
with open('data/training_area.geojson') as f:
    training_areas = json.load(f)
client.set_annotations(detector_id, raster_id, 'training_area', training_areas)
with open('data/validation_area.geojson') as f:
    validation_areas = json.load(f)
client.set_annotations(detector_id, raster_id, 'validation_area', validation_areas)
client.train_detector(detector_id)

# In order to detect with the trained detector see upload_and_detect.py