'''
Created on Mar 22, 2012

@author: visser
'''
import unittest
import signal
import os
import urllib2
import time
import subprocess
import json
import httplib

class Test(unittest.TestCase):
    
    proc_id = None
    
    def setUp(self):
        self.proc_id = subprocess.Popen('/usr/local/google_appengine/dev_appserver.py\
                                         --skip_sdk_update_check --port 8080 -c \
                                          /Users/visser/Development/dreamiam',
                                           shell=True)
        time.sleep(4)
        
    def encode_multipart_formdata(self, json, prop_name, prop_value):
        BOUNDARY = 'kajsdlfiu0293hoidjlf'
        CRLF = '\r\n'
        L = []
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="ROOT"')
        L.append('')
        L.append(json)
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (prop_name, prop_name))
        L.append('Content-Type: %s' % 'audio/mp4')
        L.append('')
        L.append(prop_value)
        L.append('--' + BOUNDARY + '--')
        L.append('')
        body = CRLF.join(L)
        content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
        return content_type, body
        
    def post_multipart(self, json, prop_name, prop_value):
        content_type, body = self.encode_multipart_formdata(json, prop_name, prop_value)
        h = httplib.HTTPConnection('localhost', 8080)
        h.putrequest('POST', '/api')
        h.putheader('Content-Type', content_type)
        h.putheader('Content-Length', str(len(body)))
        h.endheaders()
        h.send(body)
        return h.getresponse().read()
        
    def testSendURLConnection(self):
        
        #Normal CREATE!
        newObj = {'__type':'Entry',
                  'tags':['one','two']}
        createRequest = urllib2.Request('http://localhost:8080/api', 
                                        json.dumps(newObj),
                                        {'Content-Type':'application/json'})
        newObjFd = urllib2.urlopen(createRequest)
        newObjId = int(newObjFd.read())
        
        getObjBack = urllib2.urlopen('http://localhost:8080/api/Entry/%d' % newObjId)
        fromServer = getObjBack.read()
        print str(fromServer)
        newObjResult = json.loads(fromServer)
        self.assertDictEqual(
                        {'__type':'Entry',
                         '__id':newObjId,
                         'tags':['one','two']}, 
                             newObjResult, 
                             'returned from server correctly?')
        #Nested CREATE!
        newObj = {'__type':'Entry',
                  'user':{'__type':'User',
                          'twitterHandle':'you',
                          'devices':['one','two']}}
        createRequest = urllib2.Request('http://localhost:8080/api', 
                                        json.dumps(newObj),
                                        {'Content-Type':'application/json'})
        newObjFd = urllib2.urlopen(createRequest)
        newObjId = int(newObjFd.read())
        
        getObjBack = urllib2.urlopen('http://localhost:8080/api/Entry/%d' % newObjId)
        newObjResult = json.loads(getObjBack.read())
        self.assertDictContainsSubset(
                        {'__type':'Entry',
                         '__id':newObjId}, 
                             newObjResult, 
                             'main entry')
        self.assertDictContainsSubset(
                        {'__type':'User',
                         'twitterHandle':'you',
                         'devices':['one','two']}, 
                             newObjResult['user'], 
                             'user')
        
        #Check all OBJ GET
        allObjs = urllib2.urlopen('http://localhost:8080/api')
        allObjsList = json.loads(allObjs.read())
        self.assertEqual(3, len(allObjsList), 'Check to make sure we have all the objs')


        #Check DELETE
        conn = httplib.HTTPConnection('localhost:8080')
        conn.request('DELETE', '/api?force=yes') 
        
        allObjs = urllib2.urlopen('http://localhost:8080/api')
        allObjsList = json.loads(allObjs.read())
        self.assertEqual(0, len(allObjsList), 'Check to make sure we have all the objs')
        
        #Check Multipart upload
        self.post_multipart(json.dumps({'__type':'Entry'}), 'sound', 'abc123')

        #Get all
        allObjs = urllib2.urlopen('http://localhost:8080/api/Data')
        allObjsList = json.loads(allObjs.read())
        self.assertEqual(1, len(allObjsList), 'Check to make sure we have all the objs')
        
        #Get back data
        dataId = allObjsList[0]['__id']
        allObjs = urllib2.urlopen('http://localhost:8080/api/Data/%d' % dataId)
        self.assertEqual('abc123', allObjs.read(), 'Correct Data stored?')

        #Delete both the object and its nested child
        allObjs = urllib2.urlopen('http://localhost:8080/api/Entry')
        allObjsList = json.loads(allObjs.read())
        entryId = allObjsList[0]['__id']

        conn = httplib.HTTPConnection('localhost:8080')
        conn.request('DELETE', '/api/Entry/%d?propogate=sound' % entryId) 
        
        allObjs = urllib2.urlopen('http://localhost:8080/api')
        allObjsList = json.loads(allObjs.read())
        self.assertEqual(0, len(allObjsList), 'Check to make sure we have all the objs')
        
        
        #Overwrite an object with different value
        newObj = {'__type':'Entry',
                  'tags':['one','two'],
                  'location':{'__type':'GeoPt', 'lat':32.124, 'lon':-123.543}}
        createRequest = urllib2.Request('http://localhost:8080/api', 
                                        json.dumps(newObj),
                                        {'Content-Type':'application/json'})
        newObjFd = urllib2.urlopen(createRequest)
        newObjId = int(newObjFd.read())
        
        newObj['__id'] = newObjId
        newObj['tags'] = ['one']
        newObj['location'] = {'__type':'GeoPt', 'lat':-32.124, 'lon':123.543}
        createRequest = urllib2.Request('http://localhost:8080/api', 
                                        json.dumps(newObj),
                                        {'Content-Type':'application/json'})
        newObjFd = urllib2.urlopen(createRequest)
        newObjId = int(newObjFd.read())
       
        getObjBack = urllib2.urlopen('http://localhost:8080/api/Entry/%d' % newObjId)
        newObjResult = json.loads(getObjBack.read())

        self.assertDictEqual(
                        {'__type':'Entry',
                         '__id':newObjId,
                         'tags':['one'],
                         'location':{'__type':'GeoPt', 'lat':-32.124, 'lon':123.543}}, 
                             newObjResult, 
                             'returned from server correctly?')        
        
    def tearDown(self):
        os.kill(self.proc_id.pid, signal.SIGINT)

if __name__ == '__main__':
    unittest.main()
