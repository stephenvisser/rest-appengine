'''
Created on Apr 13, 2012

@author: visser
'''

import webapp2
from google.appengine.ext.webapp import blobstore_handlers
import urllib
import json

from google.appengine.ext.ndb import blobstore

class Prepare(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/file_upload')
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(upload_url))

class Upload(blobstore_handlers.BlobstoreUploadHandler):
    '''
    This will manage any uploads that we make.
    
    '''

#    def delete(self):
#        blobstore.delete(self.request.get('key') or '')

    def post(self):
        '''
        This will implicitly store the information. Simply redirect
        any gets back to the form
        '''
        
        upload_files = self.get_uploads('soundbyte')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps('/file_download/' + str(blob_info.key())))

class Download(blobstore_handlers.BlobstoreDownloadHandler):
    '''
    Manages the downloads
    '''
    def get(self, key):
        '''
        Grab the resource with the given ID and return it
        '''
        key = str(urllib.unquote(key))

        if not blobstore.get(key):
            self.error(404)
        else:
            self.send_blob(key)
