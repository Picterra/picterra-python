<a href="https://picterra.ch">
    <img
        src="https://storage.googleapis.com/cloud.picterra.ch/public/assets/logo/picterra_logo_640.png"
        alt="Picterra logo" title="Picterra" align="right" height="40" />
</a>

# Picterra Python API Client

![Tests](https://github.com/Picterra/picterra-python/workflows/lint%20and%20tests/badge.svg?branch=master)

Easily integrate state-of-the-art machine learning models in your app

```python
from picterra import APIClient

# Replace this with the id of one of your detectors
detector_id = 'd552605b-6972-4a68-8d51-91e6cb531c24'

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
print('Uploading raster...')
raster_id = client.upload_raster('data/raster1.tif', name='a nice raster')
print('Upload finished, starting detector...')
result_id = client.run_detector(detector_id, raster_id)
client.download_result_to_feature_collection(result_id, 'result.geojson')
print('Detection finished, results are in result.geojson')
```



## Installation

```
pip install git+https://github.com/Picterra/picterra-python.git
```

See the `examples` folder for examples.

## API Reference and User Guide available on [Read the Docs](https://picterra-python.readthedocs.io/)

[![Read the Docs](https://storage.googleapis.com/cloud.picterra.ch/external/assets/python_api_docs_screenshot.png)](https://picterra-python.readthedocs.io/)


## Development

In order to test locally, run `python setup.py test`
