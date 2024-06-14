#!/usr/bin/env python3
"""
This example shows how to upload outlines/annotations to a mutliclass detector

Instructions to test:
- Upload 'raster1.tif' in a new detector
- Create 2 classes in the detector (it should have 3 classes total)
- Write down the raster/detector id and replace them below
"""
import json
from picterra import APIClient

# TODO: Adapt IDs
DETECTOR_ID = "9a16c150-ae24-4bb6-9378-085955c7a4ac"
RASTER_ID = "89139314-0bc0-4243-9357-b91c502513b2"

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
detector_info = client.get_detector(DETECTOR_ID)


def get_class_id(class_name):
    for class_info in detector_info["classes"]:
        if class_info["name"] == class_name:
            return class_info["id"]
    raise RuntimeError("Class with name=%s not found" % class_name)


def load_annotations(name):
    with open("data/%s" % name) as f:
        fc = json.load(f)
    return fc


client.set_annotations(
    DETECTOR_ID,
    RASTER_ID,
    "outline",
    load_annotations("outline.geojson"),
    class_id=get_class_id("class0"),
)
client.set_annotations(
    DETECTOR_ID,
    RASTER_ID,
    "outline",
    load_annotations("outline2.geojson"),
    class_id=get_class_id("class1"),
)
client.set_annotations(
    DETECTOR_ID,
    RASTER_ID,
    "outline",
    load_annotations("outline3.geojson"),
    class_id=get_class_id("class2"),
)
