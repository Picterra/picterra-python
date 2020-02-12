from picterra import APIClient

client = APIClient(api_key='1234')
for raster in client.rasters_list():
    print('raster id=%s, name=%s, status=%s' % (raster['id'], raster['name'], raster['status']))
