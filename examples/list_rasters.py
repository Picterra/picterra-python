from picterra import APIClient

client = APIClient(api_key='1234')
for raster in client.list_rasters():
    print('raster id=%s, name=%s, status=%s' % (raster['id'], raster['name'], raster['status']))
