'''
Created on Mar 22, 2012

@author: visser
'''
import unittest

from com.dreamiam import parser
from com.dreamiam import model
from google.appengine.ext import db
import json
from google.appengine.ext import testbed

class Test(unittest.TestCase):
    
    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()

    def testObjectWithKeys(self):
        
        dataKey = model.Data(contentType='audio/mp4',data='j20983rh92iuh3oubdiub2308e20h38hd0j2038dh028hf082h30r').put()
        userKey = model.User(devices=['device1','device2'], twitterHandle='me').put()
        
        entryKey = model.Entry(tags=['tag1', 'tag2', 'tag3'],
                            user = userKey,
                            timestamp=1234556,
                            location=model.GeoPt(lat=-13.321,lon=122.332),
                            sound=dataKey,
                            description = 'This is an extended description of the entry').put()
        result = json.loads(parser.get_json_string(entryKey))
        self.assertDictContainsSubset( {'__type':'Entry',
                              '__id':entryKey.id(),
                              'timestamp':1234556,
                              'description':'This is an extended description of the entry',
                              'tags':['tag1', 'tag2', 'tag3']},
                              result,
                            'Ensuring all keys are present')
        userResult = result['user']
        self.assertDictEqual({'__id':userKey.id(),
                                       '__type':'User',
                                       'twitterHandle':'me',
                                       'devices':['device1','device2']},
                                       userResult,'User')
        dataResult = result['sound']
        self.assertDictEqual({'__id':dataKey.id(),'__type':'Data'}, dataResult, 'Sound Properties are present')
        
        locationResult = result['location']
        self.assertDictEqual({'__type':'GeoPt','lat':-13.321,'lon':122.332}, locationResult, 'GeoPt is correct')
        
    def testObjectWithLinks(self):
        userKey = model.User(devices=['device1','device2'], twitterHandle='me').put()
        
        #CLIENT CODE
        userDict = {'__type':'User','__id':userKey.id()}
        geoDict = {'__type':'GeoPt',
                   'lat':12.431,
                   'lon':-22.321}
        dictObj = {'tags':['tag1', 'tag2', 'tag3'],
                  'user' : userDict,
                  'timestamp':1234556,
                  'location': geoDict,
                  'sound':None,
                  'description': 'This is an extended description of the entry',
                  '__type':'Entry'}
        
        #TOTALLY JUST A STRING
        jsonResult = json.dumps(dictObj)
        
        #SERVER
        obj = parser.put_model_obj(jsonResult)
        backAgain = db.get(obj.key())
        
        self.assertEqual(set(['tag1', 'tag2', 'tag3']), set(backAgain.tags), 'Tags')
        self.assertEqual(userKey.id(), backAgain.user.key().id(), 'User')
        self.assertEqual(1234556, backAgain.timestamp, 'Timestamp')
        self.assertEqual(12.431, backAgain.location.lat, 'Latitude')
        self.assertEqual(-22.321, backAgain.location.lon, 'Longitude')
        
    def testNestedAdd(self):
        userDict = {'__type':'User',
                    'devices':['device1','device2'],
                    'twitterHandle':'me'}
        geoDict = {'__type':'GeoPt',
                   'lat':12.431,
                   'lon':-22.321}
        dictObj = {'tags':['tag1', 'tag2', 'tag3'],
                  'user' : userDict,
                  'timestamp':1234556,
                  'location': geoDict,
                  'sound':None,
                  'description': 'This is an extended description of the entry',
                  '__type':'Entry'}
        
        jsonResult = json.dumps(dictObj)
        obj = parser.put_model_obj(jsonResult)
        backAgain = db.get(obj.key())
        
        self.assertEqual(set(['device1','device2']),set(backAgain.user.devices), 'User/Devices')
        self.assertEqual('me',backAgain.user.twitterHandle, 'User/Twitter')
        
    def testSubset(self):
        entryKey = model.Entry( timestamp=1).put()
        entryString = parser.get_json_string(entryKey)
        actualDict = json.loads(entryString)
        self.assertDictEqual({'__type':'Entry', '__id':entryKey.id(), 'timestamp':1}, actualDict,'There shouldn\'t be nulls')
        
    def testOverwrite(self):
        userKey1 = model.User(devices=['device1','device2'], twitterHandle='me').put()
        userKey2 = model.User(devices=['device3','device4'], twitterHandle='you').put()

        entryKey = model.Entry(tags=['tag1', 'tag2', 'tag3'],
                    timestamp=1,
                    location=model.GeoPt(lat=-13.321,lon=122.332),
                    user = userKey1,
                    description = 'This is an extended description of the entry').put()
                    
        backAgain = db.get(entryKey)
        self.assertEqual(1, backAgain.timestamp, 'Timestamp = 1 to start')
        self.assertEqual(userKey1.id(), backAgain.user.key().id(), 'User num')
        self.assertAlmostEqual(-13.321,backAgain.location.lat,3)
        
        dictObj = {'tags':['tag1', 'tag2', 'tag3', 'tag4'],
                  'timestamp':2,
                  'description': 'This is a NEW description',
                  'location':None,
                  'user':{'__type':'User','__id':userKey2.id()},
                  '__type':'Entry',
                  '__id':entryKey.id()}
        
        jsonResult = json.dumps(dictObj)
        obj = parser.put_model_obj(jsonResult)
        objKey = obj.key()
        backAgain = db.get(objKey)
        self.assertEqual(2, backAgain.timestamp, 'Timestamp = 2 at end')
        self.assertEqual(userKey2.id(), backAgain.user.key().id(), 'User num')
        self.assertIsNone(backAgain.location,'Location has been zerod out')
        
    def testExceptionCases(self):
        dictObj = {'tags':['tag1', 'tag2', 'tag3', 'tag4'],
          'timestamp':2,
          'description': 'This is a NEW description',
          'location':None,
          'user':None}

        jsonResult = json.dumps(dictObj)
        
        #Checks that the SyntaxError is raised when we try to perform the 
        #to_model_object function with the jsonResult
        self.assertRaises(SyntaxError, parser.put_model_obj, jsonResult)


        dictObj = {'tags':['tag1', 'tag2', 'tag3', 'tag4'],
          'timestamp':2,
          'description': 'This is a NEW description',
          'location':None,
          'user':None,
          '__type':'Monkeys'}

        jsonResult = json.dumps(dictObj)
        
        #Checks that the SyntaxError is raised when we try to perform the 
        #to_model_object function with the jsonResult
        self.assertRaises(SyntaxError, parser.put_model_obj, jsonResult)

    def tearDown(self):
        self.testbed.deactivate()

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()