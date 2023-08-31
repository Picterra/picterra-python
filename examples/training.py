#!/usr/bin/env python3

import json

from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()

# Create a new detector (its type is 'count' by default)
detector_id = client.create_detector("My first detector")

# Upload a training raster for the detector above
raster_id = client.upload_raster("data/raster1.tif", name="a nice raster")
client.add_raster_to_detector(raster_id, detector_id)

# Add annotations
with open("data/outline.geojson") as f:
    outlines = json.load(f)
client.set_annotations(detector_id, raster_id, "outline", outlines)
with open("data/training_area.geojson") as f:
    training_areas = json.load(f)
client.set_annotations(detector_id, raster_id, "training_area", training_areas)
with open("data/validation_area.geojson") as f:
    validation_areas = json.load(f)
client.set_annotations(detector_id, raster_id, "validation_area", validation_areas)

# Train the detector
client.train_detector(detector_id)

# At this point your detector is ready to predict: see upload_and_detect.py in order
# to launch a prediction on a raster; you can also use one of the raster already added above.
