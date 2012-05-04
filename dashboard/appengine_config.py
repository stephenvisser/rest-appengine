model_settings = {
    'path': 'model'
}

import webapp2

from rest import rest_api
from rest import file_manager

app = webapp2.WSGIApplication([('/api.*', rest_api.Rest), ('/prepare_upload', file_manager.Prepare), ('/file_upload', file_manager.Upload), ('/file_download/([^/]+)', file_manager.Download)], debug=True)