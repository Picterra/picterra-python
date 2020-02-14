from picterra import APIClient

client = APIClient(api_key='1234')
raster_id = client.upload_raster('data/raster1.tif', name='a nice raster')
print('Uploaded raster=', raster_id)
