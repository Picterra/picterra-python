import os
import requests
import logging
from urllib.parse import urljoin


logger = logging.getLogger()


class APIClient():
    def __init__(self, api_key, base_url=None):
        if base_url is None:
            base_url = os.environ.get('PICTERRA_BASE_URL', 'https://app.picterra.ch/public/api/v1/')
        logger.info('using base_url=%s', base_url)
        self.base_url = base_url
        self.sess = requests.Session()
        self.sess.headers.update({'X-Api-Key': api_key})

    def _api_url(self, path):
        return urljoin(self.base_url, path)

    def rasters_list(self):
        """
        Returns the list of rasters stored in the account

        Returns: A list of rasters dictionaries

            ```
                {
                    'id': '42',
                    'status': 'ready',
                    'name': 'raster1'
                },
                {
                    'id': '43',
                    'status': 'ready',
                    'name': 'raster2'
                }
            ```
        """
        resp = self.sess.get(self._api_url('rasters/'))
        return resp.json()
