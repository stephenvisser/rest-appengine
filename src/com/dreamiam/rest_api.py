'''
Created on Mar 23, 2012

@author: visser
'''

import webapp2
import json
import logging
import re

from google.appengine.ext.db import metadata

from com.dreamiam import parser
from com.dreamiam.model import * #@UnusedWildImport

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
        
    def post(self):
        '''Handles POST requests'''

        match = re.match(r'^/api$',
                         self.request.path_info)
        if match:
            if self.request.content_type == 'application/json':
                #Simple: Load the JSON values that were sent to the server
                newObj = parser.put_model_obj(self.request.body)
            elif self.request.content_type.startswith('multipart/form-data'):
                
                #Iterate through all the fields in this multipart request
                itemIter = iter(self.request.POST.items())
                #We don't care what the root property name is, just the value
                root_json_value = itemIter.next()[1]
                
                #We are cheating a little by adding the properties in the data parts
                #of the multipart requests in as strings. This is just to avoid
                #multiple writes to the DB.
                root_dict = json.loads(root_json_value)

                for next_prop_name, next_form_field in itemIter:
                    data_key = Data(data=db.Blob(next_form_field.value),contentType=next_form_field.type).put()
                    root_dict[next_prop_name] = parser.dict_from_key(data_key)
                
                newObj = parser.put_model_obj(json.dumps(root_dict))
            else:
                raise NotImplementedError('We don\'t support this content-type %s' 
                                          % self.request.content_type)
                
            #Write back the id of the new object
            self.response.write(str(newObj.key().id()))
        else:
            raise MalformedURLException("When posting, we only support the '/api' URL")
        
    def _convert_filter_to_type(self,model_cls, property_name, filter_value):
        '''Converts a filter value to its appropriate data type based on its property value'''

        #Gets the data_type (Property objects we define on our model objects)
        attrType = getattr(model_cls, property_name).data_type

        if issubclass(attrType, basestring):
            queryValue = filter_value
        elif issubclass(attrType, int):
            queryValue = int(filter_value)
        elif issubclass(attrType, db.Model):
            queryValue = db.Key.from_path(attrType.__name__, int(filter_value))
        else:
            raise MalformedURLException("We can't handle a filter on property \
                '%s' in class '%s' of type: '%s'" % (property_name, model_cls, attrType))
        return queryValue


    def _perform_filter(self, cls, propertyFilter):
        '''Performs a search for all items in a filter'''
        allItems = []
        filter_result = re.match(r'(?P<property_name>/w+):(?P<filter_value>/w+)', propertyFilter)
        if not filter_result:
            raise MalformedURLException("The filter is malformed: '%s'" % propertyFilter)
        
        #=======================================================================
        # Create local variables for all the request variables
        #=======================================================================
        load_content = self.request.get('load_content')
        existPolicy = self.request.get('non_exist')
        prop_name = filter_result.group('property_name')
        filter_value = filter_result.group('filter_value')
        
        
        converted_filter_value = self._convert_filter_to_type(cls, prop_name,filter_value)
        #Iterate through the responses
        for item in cls.gql('WHERE %s = :1' % prop_name, converted_filter_value):
            if load_content == 'all':
                allItems.append(item)
            else:
                allItems.append(item.key())
        
        #If the policy is to create an object if it doesn't already exist,
        #we should do that here
        if len(allItems) == 0 and existPolicy == 'create':
            brandNewObj = cls(**{prop_name:filter_value})
            bnoKey = brandNewObj.put()
            if load_content == 'none':
                allItems.append(bnoKey)
            else:
                allItems.append(brandNewObj)
        return allItems

    def _write_all_objects_of_type(self, model_type):
        '''This finds all objects of a given type and writes them as a response'''
        cls = globals()[model_type]

        propertyFilter = self.request.get('filter')
        if propertyFilter:
            #Finds all items that match the filter
            allItems = self._perform_filter(cls, propertyFilter)

        else:    
            #Finds the class that was specified from our list of global objects
            #and create a Query for all of these objects. Then iterate through
            #and collect the IDs
            keysOnlyBool = self.request.get('load_content') != 'all'
            allItems = []
            for item in cls.all(keys_only=keysOnlyBool):
                allItems.append(item)

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
            data = db.get(db.Key.from_path(model_type, model_id))
            self.response.headers['Content-Type'] = str(data.contentType)
            self.response.write(data.data)
        else:
            obj_key = db.Key.from_path(model_type, model_id)
            objectString = parser.get_json_string(obj_key)
            #Return the values in the entity dictionary
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(objectString)
            
    def _write_all(self):
        '''Writes every single entity stored in the DB'''

        allEntities = []
        for k in metadata.Kind.all():
            if not k.kind_name.startswith('_'):
                for o in globals()[k.kind_name].all(keys_only=True):
                    allEntities.append(o)
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
                    deleteObjKey = db.Key.from_path(object_type, int(object_id))
                    returned_obj = db.get(deleteObjKey)
                    logging.getLogger().warn('Attempting to delete: %s, with id: %s and got this: %s' %(object_type, object_id, returned_obj))
                    if property_to_delete:
                        db.delete(getattr(returned_obj,property_to_delete))
                    db.delete(deleteObjKey)
                else:
                    if self.request.get('force') == 'yes':
                        keysOnlyBool = property_to_delete == None
                        for key in globals()[object_type].all(keys_only=keysOnlyBool):
                            if property_to_delete:
                                db.delete(getattr(key,property_to_delete))
                            db.delete(key)
                    else:
                        raise SyntaxError("MUST use 'force'='yes' to do this mode of delete")
            else:
                if self.request.get('force') == 'yes':
                    for k in metadata.Kind.all():
                        if not k.kind_name.startswith('_'):
                            for o in globals()[k.kind_name].all(keys_only=True):
                                db.delete(o)
                else:
                    raise SyntaxError("MUST use 'force'='yes' to do this mode of delete")
        else:
            raise MalformedURLException('Error when parsing URL - invalid syntax: %s' 
                                        % self.request.path_info)
        
app = webapp2.WSGIApplication([('/api.*', Rest)], debug=True)
