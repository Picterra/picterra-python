<a href="https://picterra.ch">
    <img
        src="https://storage.googleapis.com/cloud.picterra.ch/public/assets/logo/picterra_logo_640.png"
        alt="Picterra logo" title="Picterra" align="right" height="40" />
</a>

# Picterra Python API Client

![Tests](https://github.com/Picterra/picterra-python/workflows/lint%20and%20tests/badge.svg?branch=master)
[![Documentation Status](https://readthedocs.org/projects/picterra-python/badge/?version=latest)](https://picterra-python.readthedocs.io/en/latest/?badge=latest)
[![PyPI - Version](https://img.shields.io/pypi/v/picterra)](https://pypi.org/project/picterra/)

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
pip install picterra
```

See the `examples` folder for examples.

## API Reference and User Guide available on [Read the Docs](https://picterra-python.readthedocs.io/)

[![Read the Docs](https://storage.googleapis.com/cloud.picterra.ch/external/assets/python_api_docs_screenshot.png)](https://picterra-python.readthedocs.io/)


## Development

### Setup
Make sure you have `Python` and `pip` in your OS and create a virtual environment in the root folder, eg

```bash
python3 -m venv .venv
source .venv/bin/activate 
```

Running
```bash
pip install --editable '.[lint,test]'
```
would allow to run test and linting locally, and also avoid re-installing the library every time you change the code.

### Running tests
In order to test locally, run:
```bash
pytest
```

## Release process

1. Bump the version number in `setup.py`
2. Manually run the [publish to testpypi workflow](https://github.com/Picterra/picterra-python/actions/workflows/python-publish-testpypi.yml)
3. Check the publication result on [testpypi](https://test.pypi.org/project/picterra/)
4. Create a release through github
  4.1. Make sure you create a new tag vX.Y.Z through the release UI
  4.2. Click the "generate release notes" button in the UI to get release notes
5. The 'publish to pypi' workflow should automatically run
  5.1. Note this will *not* work if you create the release first as a draft - you
       have to create it immediatly
6. Updated package should be available on [pypi](https://pypi.org/project/picterra/)

