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
    def __init__(self, message):
        Exception.__init__()
        self.message = message

class Rest(webapp2.RequestHandler):
    '''
    This class provides a RESTful API from which we can
    completely control our data model
    '''
        
    def post(self):
        logging.getLogger().info('The type is %s' % self.request.content_type)
        if self.request.content_type == 'application/json':
            #Simple: Load the JSON values that were sent to the server
            newObj = parser.put_model_obj(self.request.body)
        elif self.request.content_type.startswith('multipart/form-data'):
            #Load the ROOT entity with JSON, and then add the sound part
            itemIter = iter(self.request.POST.items())
            #We don't care what the root property name is
            root_json_string = itemIter.next()[1]
            root_dict = json.loads(root_json_string)

            for next_prop_name, next_form_field in itemIter:
                data_key = Data(data=db.Blob(next_form_field.value),contentType=next_form_field.type).put()
                root_dict[next_prop_name] = parser.dict_from_key(data_key)
            
            newObj = parser.put_model_obj(json.dumps(root_dict))
        else:
            raise NotImplementedError('We don\'t support this content-type %s' 
                                      % self.request.content_type)
        
        self.response.write(str(newObj.key().id()))

        #TODO Notifications should be pushed to the app

        #TODO We should check if the user already has the deviceToken that was
        #used to make the journal entry

        #TODO Push Notifications could use badges in the future

        #This isn't really efficient, but for now, we will refresh the
        #memcache value tags list every time we push a new value to the
        #server.
        
    def _convert_filter_to_type(self,model_cls, property_name, filter_value):
        '''Converts a filter value to its appropriate data type based on its property value'''

        attrType = getattr(model_cls, property_name).data_type

        if issubclass(attrType, basestring):
            queryValue = filter_value
        elif issubclass(attrType, int):
            queryValue = int(filter_value)
        elif issubclass(attrType, db.Model):
            queryValue = db.Key.from_path(attrType.__name__, int(filter_value))
        else:
            raise MalformedURLException("We can't handle a filter on property \
                '%s' in class '%s' of type: '%s'" % [property_name, model_cls, attrType])
        return queryValue

    def _write_all_objects_of_type(self, model_type):
        allItems = []
        cls = globals()[model_type]

        propertyFilter = self.request.get('filter')
        if propertyFilter:
            #If we are filtering by a property
            filter_result = re.match(r'(?P<property_name>/w+):(?P<filter_value>/w+)',propertyFilter)
            if not filter_result:
                raise MalformedURLException("The filter is malformed: '%s'" % propertyFilter)

            allContentBool = self.request.get('load_content') == 'all'

            converted_filter_value = self._convert_filter_to_type(cls, 
                        filter_result.group('property_name'), 
                        filter_result.group('filter_value'))

            #Iterate through the responses
            for item in cls.gql('WHERE %s = :1' % filter_result.group('property_name'),
                                 converted_filter_value):
                if allContentBool:
                    allItems.append(item)
                else:
                    allItems.append(item.key())
            
            #If the policy is to create an object if it doesn't already exist,
            #we should do that here
            existPolicy = self.request.get('non_exist')
            if len(allItems) == 0 and existPolicy == 'create':
                brandNewObj = cls(**{filter_result.group('property_name'): 
                        filter_result.group('filter_value')})
                bnoKey = brandNewObj.put()
                loadContentPolicy = self.request.get('load_content')
                if loadContentPolicy == 'none':
                    allItems.append(bnoKey)
                else:
                    allItems.append(brandNewObj)

        else:    
            #Finds the class that was specified from our list of global objects
            #and create a Query for all of these objects. Then iterate through
            #and collect the IDs
            keysOnlyBool = self.request.get('load_content') != 'all'

            for item in cls.all(keys_only=keysOnlyBool):
                allItems.append(item)

        #Write JSON back to the client
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(parser.get_json_string(allItems))
        
    def _write_object_with_id(self, model_type, model_id):
        #Convert the ID to an int, create a key and retrieve the object
                
        if model_type == 'Data':
            #Convert the content-type to string or else badness happens
            data = db.get(db.Key.from_path(model_type, model_id))
            self.response.headers['Content-Type'] = str(data.contentType)
            self.response.write(data.data)
        else:
            obj_key = db.Key.from_path(model_type, model_id)
            objectString = parser.get_json_string(obj_key)
#            logging.getLogger().warn('The object: %s' % objectString)
            logging.getLogger().warn('Retrieved: %s from key: %s with type: %s and id %d' % (objectString, str(obj_key), model_type, model_id))


            #Return the values in the entity dictionary
            self.response.headers['Content-Type'] = "application/json"
            self.response.write(objectString)
            
    def _write_all(self):
        allEntities = []
        for k in metadata.Kind.all():
            if not k.kind_name.startswith('_'):
                for o in globals()[k.kind_name].all(keys_only=True):
                    allEntities.append(o)
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(parser.get_json_string(allEntities))
    
    def get(self):
        match = re.match(r'^/api(?:/(?P<type>\w+))?(?:/(?P<id>\d+))?$',
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
            raise MalformedURLException('Error when parsing URL - invalid syntax: %s' 
                            % self.request.path_info)

    def delete(self):
        logging.getLogger().warn(self.request.path_info)
        match = re.match(r'^/api(?:/(?P<type>\w+))?(?:/(?P<id>\w+))?$',
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
                    keysOnlyBool = property_to_delete == None
                    for key in globals()[object_type].all(keys_only=keysOnlyBool):
                        if property_to_delete:
                            db.delete(getattr(key,property_to_delete))
                        db.delete(key)
            else:
                if self.request.get('force'):
                    for k in metadata.Kind.all():
                        if not k.kind_name.startswith('_'):
                            for o in globals()[k.kind_name].all(keys_only=True):
                                db.delete(o)
                else:
                    raise Exception("If you are trying to delete everything, use 'force'")
        else:
            raise MalformedURLException('Error when parsing URL - invalid syntax: %s' 
                                        % self.request.path_info)
        
app = webapp2.WSGIApplication([('/api.*', Rest)], debug=True)