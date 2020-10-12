from picterra import APIClient

# Set the PICTERRA_API_KEY environment variable to define your API key
client = APIClient()

raster_id = client.upload_raster('data/raster1.tif', name='a nice raster')
print('Uploaded raster=', raster_id)

for raster in client.list_rasters():
    print('raster id=%s, name=%s, status=%s' % (raster['id'], raster['name'], raster['status']))

client.delete_raster(raster_id)
print('Deleted raster=', raster_id)
