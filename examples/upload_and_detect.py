from picterra import APIClient

# Replace this with the id of one of your detectors
detector_id = 'd552605b-6972-4a68-8d51-91e6cb531c24'
# Replace this with the id of a folder in which the
# raster should be uploaded.
folder_id = '63207fe9-32b8-410f-a72d-00803cca7bf3'

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()
print('Uploading raster...')
raster_id = client.upload_raster('data/raster1.tif', name='a nice raster', folder_id=folder_id)
print('Upload finished, starting detector...')
result_id = client.run_detector(detector_id, raster_id)
client.download_result_to_file(result_id, 'result.geojson')
print('Detection finished, results are in result.geojson')