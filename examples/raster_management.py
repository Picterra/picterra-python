from picterra import APIClient

client = APIClient(api_key='1234')

raster_id = client.upload_raster('data/raster1.tif', name='a nice raster')
print('Uploaded raster=', raster_id)

for raster in client.list_rasters():
    print('raster id=%s, name=%s, status=%s' % (raster['id'], raster['name'], raster['status']))

client.delete_raster(raster_id)
print('Deleted raster=', raster_id)
