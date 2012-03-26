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

def dict_from_key(key):
    return  {CLASS_TYPE_STR:key.kind(),ID_STR:key.id()}

def put_model_obj(json_string):
    '''
    Converts a string to a Model object as necessary
    Returns an OBJ of the string that was stored.
    NOTE: AUTOMATICALLY STORES THE OBJECT;
    This is to make parsing this information more performant
    '''
    list_of_objects = []
    def _hook_to_object(dct):
        '''
        This is the method that is called every time we are decoding a JSON
        object. Since objects must be stored as their keys, this method makes
        the assumption that if only the __type and __id properties are present,
        we will just create a reference. If the additional properties are 
        present AND __id, then we will overwrite the existing object without 
        any discernment. Finally, if no __id is present, we will store this as
        a brand new object
        '''
        try:
            #Retrieves the class type and ID which are special tags
            clsType = dct[CLASS_TYPE_STR]
            #Using get() here means we won't get a KeyError (just None)
            clsId = dct.get(ID_STR)
        
            if clsId and len(dct) == 2:
                #If only the __type and __id properties exist
                return Key.from_path(clsType, clsId)

            dictCopy = dict((key, value) for key, value in dct.iteritems() if not key.startswith('__'))
            
            try:
                if clsId:
                    #If there is an __id property, we should set the key of the
                    #object too
                    dictCopy['key'] = Key.from_path(clsType, clsId)

                #This line is slightly confusing. It will look up the desired
                #class in the list of global names and create an object with all
                #instance variables initialized using the dictionary values
                newObj = globals()[clsType](**dictCopy)
            
                if isinstance(newObj, Model):
                    #We are populating a list of objects that are to be stored
                    #implicitly into the DB. The last one added will be our root
                    #object
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
    return list_of_objects[-1]

def get_json_string(model_object_key):
    '''Converts a Model object to a string we can send to the server'''
    return json.dumps(db.get(model_object_key), cls=_ExtendedJSONEncoder)

class _ExtendedJSONEncoder(json.JSONEncoder):
    '''Custom Encoder that can handle Model objects'''
    def default(self, obj):
        '''The method called first when encoding'''
        if isinstance(obj, Key):
            #When the instance is a Key, just include the type and id
            return {CLASS_TYPE_STR:obj.kind(), ID_STR:obj.id()}
        elif isinstance(obj, Data):
            #When the instance is a model type 'Data', we obviously can't
            #send the binary (unless we encoded it as base64 -- which
            #is too expensive) so we just attach the object information
            return {CLASS_TYPE_STR:obj.key().kind(), ID_STR:obj.key().id()}
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
            dictCopy = obj.__dict__.copy()
            dictCopy[CLASS_TYPE_STR] = obj.__class__.__name__
            return dictCopy
        
        #If we haven't yet found an exact match, use the default
        return json.JSONEncoder.default(self, obj)
