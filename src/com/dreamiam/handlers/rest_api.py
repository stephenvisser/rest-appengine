'''
Created on Mar 23, 2012

@author: visser
'''

import webapp2
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

        match = re.match(r'^/api(?:/(?P<entity>\w+)(?:/(?P<id>\d+))?)?$',
                         self.request.path_info)
        if match:
            if self.request.content_type == 'application/json':
                if match.group('entity') or match.group('id'):
                    raise MalformedURLException("If you are posting data, set content-type as appropriate. If you're using json, check your url: should be '/api'")

                #Simple: Load the JSON values that were sent to the server
                newObj = parser.put_model_obj(self.request.body)
            elif self.request.content_type == 'multipart/form-data':
                content = self.request.POST.items()[0][1];
                newObj = Data(data=db.Blob(content.value),contentType=content.type);
                newObj.put();
            else:    
                #We store all others as data. This means that we remember the content
                #type and host the data at its own URL instead of embedding it in JSON
                newObj = Data(data=db.Blob(self.request.body),contentType=self.request.content_type)
                newObj.put()
                
            #Write back the id of the new object
            self.response.write(str(newObj.key().id()))
        else:
            raise MalformedURLException("When posting, we only support the '/api' URL (/api/<type>/<id> is supported for Data requests)")
        
    def _convert_filter_to_type(self,model_cls, property_name, filter_value):
        '''Converts a filter value to its appropriate data type based on its property value'''

        #Gets the data_type (Property objects we define on our model objects)
        attrType = getattr(model_cls, property_name).data_type

        logging.getLogger().info('%s is of type %s' %(property_name,attrType))
        if issubclass(attrType, basestring):
            queryValue = str(filter_value)
        elif issubclass(attrType, int):
            queryValue = int(filter_value)
        elif issubclass(attrType, db.Model):
            queryValue = db.Key.from_path(attrType.__name__, int(filter_value))
        else:
            raise MalformedURLException("We can't handle a filter on property \
                '%s' in class '%s' of type: '%s'" % (property_name, model_cls, attrType))
        return queryValue
    
    def _get_filters(self):
        filters = self.request.get_all('filter')        
        #Clever way to create a dictionary of propNames to values
        return dict(item.split(':') for item in filters)        

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
                
        #Create the class from the key
        cls = globals()[key.kind()]

        #Clever way to create a dictionary of propNames to values
        result = self._get_filters()
        
        #This is what we use to determine if it matches any possible
        #filters the user may have set
        resultArray = []
        #Start by retrieving the object
        entireObj = db.get(key)
        #Change to an array if this object doesn't exist
        if entireObj:
            #Optimistically putting the obj as a result
            resultArray.append(entireObj)
            for prop_name,filter_value in result.iteritems():
                converted_filter_value = self._convert_filter_to_type(cls, prop_name,filter_value)
                if getattr(entireObj,prop_name) != converted_filter_value:
                    #Failed to match a filter so remove it as a match
                    del resultArray[0]
                    break

        #Need to make sure the ID is set on any future objects
        result['key'] = key

        return self._create_if_necessary(cls, resultArray, result);

    def _perform_filter(self, cls):
        '''Performs a search for all items in a filter'''
                
        #=======================================================================
        # Create local variables for all the request variables
        #=======================================================================
        isLoadKeysOnly = self.request.get('load') != 'all'
        fetch,offset = self.request.get('fetch','20,0').split(',')
        
        query = db.Query(cls,keys_only=isLoadKeysOnly)

        result = self._get_filters();

        for prop_name,filter_value in result.iteritems():
            converted_filter_value = self._convert_filter_to_type(cls, prop_name,filter_value)
            query.filter(prop_name, converted_filter_value)
            logging.getLogger().info('%s is %s of type %s' %(prop_name, converted_filter_value, str(converted_filter_value.__class__)))

        #Iterate through the responses. Implicitly fetches the results
        allItems = query.fetch(int(fetch),int(offset));
        
        #If the policy is to create an object if it doesn't already exist,
        #we should do that here
        return self._create_if_necessary(cls, allItems, result)

    def _write_all_objects_of_type(self, model_type):
        '''This finds all objects of a given type and writes them as a response'''
        cls = globals()[model_type]

        allItems = self._perform_filter(cls)
        
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
            #Create the key
            obj_key = db.Key.from_path(model_type, model_id)
            
            #Do some weird voodoo magic to do the bidding of
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
        for k in metadata.Kind.all():
            if not k.kind_name.startswith('_'):
                allEntities.extend(globals()[k.kind_name].all(keys_only=isLoadKeysOnly))
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