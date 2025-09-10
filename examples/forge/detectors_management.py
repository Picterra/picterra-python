#!/usr/bin/env python3

from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()

# Create a new detector (its type is 'count' by default)
detector_id = client.create_detector("My first detector")

# Edit the above detector
client.edit_detector(detector_id, "Renamed detector", "segmentation", "bbox", 1000)

# List existing detectors
detectors_page_1 = client.list_detectors()
print("Page has " + str(len(detectors_page_1)) + " elements")
d = detectors_page_1[0]
print(
    "detector id=%s, name=%s, detection_type=%s, output_type=%s, training_steps=%d"
    % (
        d["id"],
        d["name"],
        d["configuration"]["detection_type"],
        d["configuration"]["output_type"],
        d["configuration"]["training_steps"],
    )
)
