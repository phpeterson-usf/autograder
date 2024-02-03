"""
server.py is a base class for REST servers like Canvas and Github
"""

import json
from pprint import PrettyPrinter
import requests
import urllib.error
from urllib.error import HTTPError, URLError

from actions.util import *

class Server:
    def __init__(self, host_name, token, verbose):
        self.host_name = host_name
        self.access_token = token
        self._verbose = verbose  # can't name it the same as the function


    def verbose(self, s):
        if self._verbose:
            if type(s) is dict:
                pp = PrettyPrinter(indent=4)
                pp.pprint(s)
            else:
                print(s)


    def not_found(self, s, suggestion):
        fatal(f'not found: {s}. {suggestion}')


    def add_auth_header(self, headers):
        headers['Authorization'] = f'Bearer {self.access_token}'
        return headers


    # Use requests to GET the URL
    def get_url(self, url, headers={}):
        # TODO: replace hard-coded access token with dynamic OAuth token
        headers = self.add_auth_header(headers)
        try:
            response = requests.get(url, headers=headers)
            self.verbose(f'{url} returns {response.status_code}')
            self.verbose(json.loads(response.text))
            response.raise_for_status()
        except Exception as e:
            # Callers don't have to re-warn() unless they have more info to add
            warn('get_url: ' + str(e))
            # Reraise so callers can decide whether it's fatal or not
            raise e

        content_type = response.headers['Content-Type']
        # use 'in' rather than '==' to ignore charset spec in header
        if 'application/json' in content_type:
            return json.loads(response.text)
        elif 'application/zip' in content_type:
            return response.content
        else:
            fatal(f'Unexpected Content-Type: {content_type}')


    def make_url(self, path):
        # Combine the hostname and path, creating a requestable URL
        url = f'https://{self.host_name}/{path}'
        self.verbose(url)
        return url


    def put_url(self, url, headers, data):
        headers = self.add_auth_header(headers)
        response = requests.put(url, data=data, headers=headers)
        if response.status_code != requests.codes.ok:
            self.verbose(json.loads(response.text))
        return response.status_code == requests.codes.ok
