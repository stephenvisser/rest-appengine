'''
Created on Mar 23, 2012

@author: visser
'''

import webapp2
import logging
import re

from google.appengine.ext.ndb import metadata
from google.appengine.ext import ndb

from com.dreamiam import parser
from com.dreamiam import model

class MalformedURLException(Exception):
    '''
    This is a special exception for when the URL can't be handled
    ''' 
    pass

class Rest(webapp2.RequestHandler):
    '''
    This class provides a RESTful API from which we can
    completely control our data model. It should be self-documenting to
    a certain degree
    '''
    
    def _handle_data(self, body, content_type):
        match = re.match(r'^/api(?:/(?P<entity>\w+)(?:/(?P<id>\d+))?)$',
                     self.request.path_info)
        if not match:
            raise MalformedURLException("If you are posting data, you need to specify the class type. Most likely 'Data'")

        newObj = getattr(model, match.group('entity'))(data=body,contentType=content_type, id=match.group('id'))
        newObj.put()
        return newObj
        
    def post(self):
        '''Handles POST requests'''

        if self.request.content_type == 'application/json':
            match = re.match(r'^/api$',
                         self.request.path_info)
            if not match:
                raise MalformedURLException("If you are posting data, set content-type as appropriate. If you're using json, check your url: should be '/api'")
            logging.getLogger().info("Do something here" + str(dir(parser)))
            #Simple: Load the JSON values that were sent to the server
            newObj = parser.put_model_obj(self.request.body)
        elif self.request.content_type == 'multipart/form-data':
            content = self.request.POST.items()[0][1];
            newObj = self._handle_data(content.value, content.type)
        else:    
            #We store all others as data. This means that we remember the content
            #type and host the data at its own URL instead of embedding it in JSON
            newObj = self._handle_data(self.request.body, self.request.content_type)
                
            #Write back the id of the new object
        self.response.write(str(newObj.key.id()))
        
    def _convert_filter(self, kind, propName, value):
        actualProp = getattr(kind, propName)
        actualProp._validate(value)
        logging.getLogger().info("The prop is: " + repr(actualProp))
        return propName, actualProp._to_base_type(value);
        
    def _get_filters(self, kind):
        filters = self.request.get_all('filter')        
        #Clever way to create a dictionary of propNames to values
        return dict(self._convert_filter(kind, *item.split(':')) for item in filters)        

    def _create_if_necessary(self, cls, currentEntity, values):
        if not currentEntity and self.request.get('non_exist') == 'create':
            #If the policy is to create an object if it doesn't already exist,
            #we should do that here
            brandNewObj = cls(**values)
            bnoKey = brandNewObj.put()
            if self.request.get('load') != 'all':
                currentEntity = [bnoKey]
            else:
                currentEntity = [brandNewObj]
        return currentEntity;

    def _perform_filter_on_key(self, key):
        '''Performs a search for all items in a filter'''
                
        #Clever way to create a dictionary of propNames to values
        result = self._get_filters(key.kind())
        
        #This is what we use to determine if it matches any possible
        #filters the user may have set
        resultArray = []
        #Start by retrieving the object
        entireObj = key.get()
        #Change to an array if this object doesn't exist
        if entireObj:
            #Optimistically putting the obj as a result
            resultArray.append(entireObj)
            for prop_name,filter_value in result.iteritems():
                if getattr(entireObj,prop_name) != filter_value:
                    #Failed to match a filter so remove it as a match
                    del resultArray[0]
                    break

        #Need to make sure the ID is set on any future objects
        result['key'] = key

        return self._create_if_necessary(getattr(model, key.kind()), resultArray, result);

    def _perform_filter(self, cls):
        '''Performs a search for all items in a filter'''
                
        #=======================================================================
        # Create local variables for all the request variables
        #=======================================================================
        isLoadKeysOnly = self.request.get('load') != 'all'
        
        query = cls.query()

        result = self._get_filters(cls);

        for prop_name,filter_value in result.iteritems():
            logging.getLogger().info("The filter is: " + repr(filter_value));
            query = query.filter(getattr(cls,prop_name) == filter_value)

        #Iterate through the responses. Implicitly fetches the results
        allItems = query.fetch(keys_only=isLoadKeysOnly);
        
        #If the policy is to create an object if it doesn't already exist,
        #we should do that here
        return self._create_if_necessary(cls, allItems, result)

    def _write_all_objects_of_type(self, model_type):
        '''This finds all objects of a given type and writes them as a response'''
        allItems = self._perform_filter(getattr(model, model_type))
        
        #Write JSON back to the client
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(parser.get_json_string(allItems))
        
    def _write_object_with_id(self, model_type, model_id):
        '''
        Writes an entity back to the client based on id. If the entity is
        of type Data, just the data will be written with the content-type
        with which it was stored. Otherwise, it will be json
        '''

        if model_type == 'Data':
            #Convert the content-type to string or else badness happens
            data = ndb.Key(model_type, model_id).get()
            self.response.headers['Content-Type'] = str(data.contentType)
            self.response.write(data.data)
        else:
            #Create the key
            obj_key = ndb.Key(model_type, model_id)
            
            #Do some weird voodoo magic to do the binding of
            #various optional parameters
            obj_result = self._perform_filter_on_key(obj_key)

            #We need to make these objects return arrays too
            objectString = parser.get_json_string(obj_result)
                
            #Return the values in the entity dictionary
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(objectString)
            
    def _write_all(self):
        '''Writes every single entity stored in the DB'''
        isLoadKeysOnly = self.request.get('load') != 'all'

        allEntities = []
        for k in metadata.get_kinds():
            logging.getLogger().info("TYPE:" + k)
            if not k.startswith('_'):
                allEntities.extend(getattr(model, k).query().fetch(keys_only=isLoadKeysOnly))
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(parser.get_json_string(allEntities))
    
    def get(self):
        '''Handles any and all 'get' requests'''
        match = re.match(r'^/api(?:/(?P<type>\w+)(?:/(?P<id>\d+))?)?$',
                         self.request.path_info)
        if match:
            objectType = match.group('type')
            objectId = match.group('id')
            
            if objectType:
                #If no ID, then we will return all objects of this type
                if objectId:
                    self._write_object_with_id(objectType, int(objectId))
                else:
                    self._write_all_objects_of_type(objectType)
            else:
                self._write_all()
        else:
            raise MalformedURLException('Error when parsing URL - invalid syntax: %s' % self.request.path_info)

    def delete(self):
        '''Deletes an entity as specified'''
        logging.getLogger().warn(self.request.path_info)
        match = re.match(r'^/api(?:/(?P<type>\w+)(?:/(?P<id>\w+))?)?$',
                         self.request.path_info)
        if match:
            object_type = match.group('type') 
            object_id = match.group('id')
            if object_type:
                property_to_delete = self.request.get('propogate')
                if object_id:
                    deleteObjKey = ndb.Key(object_type, int(object_id))
                    returned_obj = deleteObjKey.get()
                    logging.getLogger().warn('Attempting to delete: %s, with id: %s and got this: %s' %(object_type, object_id, returned_obj))
                    if property_to_delete:
                        getattr(returned_obj,property_to_delete).delete()
                    deleteObjKey.delete()
                else:
                    if self.request.get('force') == 'yes':
                        keysOnlyBool = property_to_delete == None
                        for key in getattr(model, object_type).all(keys_only=keysOnlyBool):
                            if property_to_delete:
                                getattr(key,property_to_delete).delete()
                            key.delete()
                    else:
                        raise SyntaxError("MUST use 'force'='yes' to do this mode of delete")
            else:
                if self.request.get('force') == 'yes':
                    for k in metadata.get_kinds():
                        if not k.kind_name.startswith('_'):
                            ndb.delete_multi(getattr(model, k.kind_name).query().fetch(keys_only=True))
                else:
                    raise SyntaxError("MUST use 'force'='yes' to do this mode of delete")
        else:
            raise MalformedURLException('Error when parsing URL - invalid syntax: %s' 
                                        % self.request.path_info)