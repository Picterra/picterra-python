import json
from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()

# Create a new detector (its type is 'count' by default)
detector_id = client.create_detector('My first detector')


# List existing detectors
for d in client.list_detectors():
    print('detector id=%s, name=%s, detection_type=%s, output_type=%s, training_steps=%d' % (
        d['id'], d['name'], d['detection_type'], d['output_type'], d['training_steps']))