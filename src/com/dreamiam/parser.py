'''
Created on Mar 22, 2012

@author: visser
'''

import json
from google.appengine.ext.db import Key
from google.appengine.ext.db import Model

from com.dreamiam.model import * #@UnusedWildImport

CLASS_TYPE_STR = '__type'
ID_STR = '__id'
REF_STR = '__ref'

def dict_from_key(key):
    return  {CLASS_TYPE_STR:key.kind(),ID_STR:key.id()}

def put_model_obj(json_string):
    '''
    Converts a string to the requisite Model object. Returns the object that
    was created from the string. NOTE that the objects (they may be nested) are
    all stored implicitly and there is no way to turn this off for now. The
    reason for this behavior is to make parsing these objects faster.
    '''
    list_of_objects = []
    def _hook_to_object(dct):
        '''
        This is the method that is called every time we are decoding a JSON
        object. Since objects must be stored as their keys, this method makes
        the assumption that if only the __type and __id properties are present,
        we will just create a reference. If any additional properties are 
        present AND __id, then we will overwrite the existing object without 
        any discernment. Finally, if no __id is present, we will store this as
        a brand new object
        '''
        try:
            #Retrieves the class type and ID which are special tags
            #WILL THROW KeyError if '__type' tag doesn't exist
            clsType = dct[CLASS_TYPE_STR]
            #Using get() here means we won't get a KeyError (just None)
            clsId = dct.get(ID_STR)
            #We now support a more robust way of defining references in our
            #code. Any JSON object that contains __reference=true will be
            #evaluated as such.
            clsReference = dct.get(REF_STR)
        
            if clsReference:
                #If only the __type and __id properties exist
                return Key.from_path(clsType, clsId)

            #Keys in JSON object that start with '__' are reserved.
            dictCopy = dict((key, value) for key, value in dct.iteritems() if not key.startswith('__'))
            
            try:
                if clsId:
                    #If there is an __id property, we should set the key of the
                    #object too in the next line. This can only be set in the
                    #constructor
                    dictCopy['key'] = Key.from_path(clsType, clsId)

                #This line is slightly confusing. It will look up the desired
                #class in the list of global names and create an object with all
                #instance variables initialized using the dictionary values
                newObj = globals()[clsType](**dictCopy)
            
                if isinstance(newObj, Model):
                    #We are keeping track of all the objects we are implicitly
                    #adding to the DB. This is the only way I could find to keep
                    #track of the actual objects so that we could return objects
                    #rather than keys; the nature of the recursive parsing will
                    #guarantee that the last object appended to this list will 
                    #be the root object
                    list_of_objects.append(newObj)
                    return newObj.put()
                return newObj
            except KeyError as key:
                #if globals() dict doesn't contain the relevant class
                newErr = SyntaxError('We don\'t support class type: %s' % clsType)
                newErr.text = str(dct)
                raise newErr
        except KeyError as key:
            #if the object dict doesn't contain the __type property
            newErr = SyntaxError('The __type property isn\'t present')
            newErr.text = str(dct)
            raise newErr

    json.loads(json_string, object_hook=_hook_to_object)
    #Return the last object in the list. This will be the root
    return list_of_objects[-1]

def get_json_string(objects):
    '''
    Uses a Model object KEY to retrieve the actual object and then return
    its string value.
    '''
    return json.dumps(objects, cls=_ExtendedJSONEncoder)

class _ExtendedJSONEncoder(json.JSONEncoder):
    '''Custom Encoder that can handle Model objects'''
    def default(self, obj):
        '''The method called first when encoding'''
        if isinstance(obj, Key):
            #When the instance is a Key, just include the type and id
            return {CLASS_TYPE_STR:obj.kind(), ID_STR:obj.id(), REF_STR:True}
        elif isinstance(obj, Data):
            #When the instance is a model type 'Data', we obviously can't
            #send the binary (unless we encoded it as base64 -- which
            #is too expensive) so we just attach the object information
            return {CLASS_TYPE_STR:obj.key().kind(), ID_STR:obj.key().id(), REF_STR:True, "__contentType":obj.contentType}
        elif isinstance(obj, Model):
            #When we have a Model object, we simply grab all properties 
            properties = obj.properties()
            dictCopy = {CLASS_TYPE_STR:obj.key().kind(), ID_STR: obj.key().id()}
            for key, propType in properties.iteritems():
                #Ignore values that are null
                value = getattr(obj,key)
                if value  or (isinstance(propType, db.ListProperty) and len(value) > 0):
                    dictCopy[key] = value
            return dictCopy
        elif isinstance(obj, object):
            #Currently this is used for db.GeoPt properties. We just
            #convert properties directly into their dictionary representation
            return str(obj)
        
        #If we haven't yet found an exact match, use the default
        return json.JSONEncoder.default(self, obj)
