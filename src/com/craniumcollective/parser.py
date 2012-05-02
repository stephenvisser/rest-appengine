'''
Created on Mar 22, 2012

@author: visser
'''
import json
import logging

from com.craniumcollective import model

from google.appengine.ext import ndb

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
        object. The difference between key objects and regular objects is that
        key objects will have the __ref property set to true. If the __ref attribute
        is not present, we create brand new objects if the __id isn't set or overwrite
        if the __id IS set.
        '''
        try:
            logging.getLogger().info('Evaluating: %s' % str(dct))

            #Retrieves the class type and ID which are special tags
            #WILL THROW KeyError if '__type' tag doesn't exist.
            #This is an ellegal state.
            clsType = dct[CLASS_TYPE_STR]
            #Using get() here means we won't get a KeyError (just None)
            clsId = dct.get(ID_STR)
            #We now support a more robust way of defining references in our
            #code. Any JSON object that contains __ref=true will be
            #evaluated as such.
            clsReference = dct.get(REF_STR)
        
            if clsReference:
                #If only the __type and __id properties exist
                return ndb.Key(clsType, clsId)

            #Keys in JSON object that start with '__' are reserved.
            dictCopy = dict((key, value) for key, value in dct.iteritems() if not key.startswith('__'))
            
            #If there is an __id property, we should set the key of the
            #object too in the next line. This can only be set in the
            #constructor
            dictCopy['id'] = clsId

            #This line is slightly confusing. It will look up the desired
            #class in the list of global names and create an object with all
            #instance variables initialized using the dictionary values
            
            logging.getLogger().info('The objects are: %s' % str(dictCopy))
            
            try:                
                newObj = getattr(model, clsType)(**dictCopy)
                logging.getLogger().info('Done creating obj')

                #We are keeping track of all the objects we are implicitly
                #adding to the DB. This is the only way I could find to keep
                #track of the actual objects so that we could return objects
                #rather than keys; the nature of the recursive parsing will
                #guarantee that the last object appended to this list will 
                #be the root object
                list_of_objects.append(newObj)
                return newObj.put()
            except KeyError as key:
                #if the model class doesn't contain the relevant class
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
        logging.getLogger().info(repr(obj))
        if isinstance(obj, ndb.Key):
            #When the instance is a Key, just include the type and id
            return {CLASS_TYPE_STR:obj.kind(), ID_STR:obj.id(), REF_STR:True}
        elif isinstance(obj, ndb.Model):
            #When we have a Model object, we simply grab all properties 
            properties = obj.to_dict()

            dictCopy = {CLASS_TYPE_STR:obj.key.kind(), ID_STR: obj.key.id()}
            for key,value in properties.iteritems():
                #Ignore values that are null or are empty arrays
                if value  or (isinstance(value, list) and len(value) > 0):
                    dictCopy[key] = value
            return dictCopy
        elif isinstance(obj, object):
            logging.getLogger().info('Interpreting: %s as an object',(obj,))
            return str(obj)
        
        #If we haven't yet found an exact match, use the default
        return json.JSONEncoder.default(self, obj)
