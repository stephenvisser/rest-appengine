'''
Created on Mar 22, 2012

@author: visser
'''
import re

from google.appengine.ext import ndb
from dateutil import parser,tz
from google.appengine.ext.ndb.google_imports import datastore_errors

#===============================================================================
# These are all the user-defined model classes.
#===============================================================================

class StringGeoPtProperty(ndb.GeoPtProperty):
    def _validate(self, value):
        if not isinstance(value, basestring):
            raise datastore_errors.BadValueError('Expected string in lat,lon format, got %r' %
                                               (value,))
    
    def _to_base_type(self, value):
        return ndb.GeoPt(value)
    
    def _from_base_type(self, value):
        return "%s,%s" %(value.lat,value.lon)


#Custom class that parses our dates as ISO 8601 strings.
class StringDateTimeProperty(ndb.DateTimeProperty):
    def _validate(self, value):
        if not isinstance(value, basestring):
            raise datastore_errors.BadValueError('Expected string in ISO 8601 format, got %r' %
                                               (value,))
    
    def _to_base_type(self, value):
        aDate = parser.parse(value)
        #Sometimes the string will have timezone information,
        #but this can't be handled by App Engine, so we will
        #remove it and assume all dates are UTC
        if aDate.tzinfo:
            aDate = aDate.astimezone(tz.tzutc())
            aDate = aDate.replace(tzinfo=None)
        return aDate
    
    def _from_base_type(self, value):
        return value.isoformat()

#This allows us to do smart inferences of keys by just giving the ID.
class SmartKeyProperty(ndb.KeyProperty):
    def _validate(self, value):
        if not ((isinstance(value, basestring) and  re.match(r'^\d+$', value)) or isinstance(value, int) or isinstance(value, ndb.Key)):
            raise datastore_errors.BadValueError('Expected integer (converted to key) or key; got %r' %
                                               (value,))
    
    def _to_base_type(self, value):
        if isinstance(value, basestring):
            return ndb.Key(self._kind, int(value))
        if isinstance(value, int):
            return ndb.Key(self._kind, value)
        return value

    def _from_base_type(self, value):
        return value

#This allows us to do smart inferences of keys by just giving the ID.
class SmartBlobProperty(ndb.BlobKeyProperty):
    def _validate(self, value):
        if not isinstance(value, basestring):
            raise datastore_errors.BadValueError('Expected the string key; got %r' %
                                               (value,))
    
    def _to_base_type(self, value):
        #Takes the last part of the URL as the key
        return ndb.BlobKey(value.split('/')[-1])

    def _from_base_type(self, value):
        return '/file_download/%s'%str(value)
    
class User(ndb.Model):
    """Models a user of the system"""
    devices = ndb.StringProperty(repeated=True);
    twitterHandle = ndb.StringProperty();

class Entry(ndb.Model):
    """Models an entry in the journal"""
    tags = ndb.StringProperty(repeated=True);
    user = SmartKeyProperty(User);
    timestamp = StringDateTimeProperty();
    location = StringGeoPtProperty();
    sound = SmartBlobProperty();
    description = ndb.TextProperty();
    
