'''
Created on Mar 22, 2012

@author: visser
'''
from google.appengine.ext import db

#===============================================================================
# These are all the user-defined model classes.
#===============================================================================

class User(db.Model):
    """Models a user of the system"""
    devices = db.StringListProperty();
    twitterHandle = db.StringProperty();

class Data(db.Model):
    """Models any arbitrary data, but in reality is mostly used for sound"""
    contentType = db.StringProperty();
    data = db.BlobProperty();

class Entry(db.Model):
    """Models an entry in the journal"""
    tags = db.StringListProperty();
    user = db.ReferenceProperty(User);
    timestamp = db.StringProperty();
    location = db.GeoPtProperty();
    sound = db.ReferenceProperty(Data);
    description = db.TextProperty();