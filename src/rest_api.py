#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on Mar 23, 2012

@author: visser
'''

import webapp2
import logging
import re
import operator
import json

from google.appengine.ext.ndb import metadata
from google.appengine.ext import ndb

import parser
import model

operator_dict = {'>': operator.gt,
                 '>=': operator.ge,
                 '=': operator.eq,
                 '!=':operator.ne,
                 '<':operator.lt,
                 '<=':operator.le}

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

        if self.request.content_type == 'application/json':
            match = re.match(r'^/api$',
                         self.request.path_info)
            if not match:
                raise MalformedURLException("The only supported POST url is: '/api'")
            #Simple: Load the JSON values that were sent to the server
            newObj = parser.put_model_obj(self.request.body)
        else:  
            raise MalformedURLException("All data must be posted using JSON. If you want to upload some data, use the file_uploader mechanism.")  
                
        #Write back the id of the new object
        self.response.write(str(newObj.key.id()))
        
    def _convert_filter(self, kind, aFilter):
        match = re.match(r'^(?P<name>\w+)(?P<operator>!=|=|>|<|>=|<=)(?P<value>.+)$', aFilter)
        if not match:
            raise MalformedURLException("Something wrong with filter: %s" % (aFilter,))

        actualProp = getattr(kind, match.group('name'))
        actualVal = actualProp._to_base_type(match.group('value'));

        #this searches through the operator dictionary for the appropriate
        #operator function and then calls it with the two operands        
        return operator_dict[match.group('operator')](actualProp, actualVal)
        
    def _get_filters(self, kind):
        '''
        There can be only one filter parameter in the URL
        '''
        filterString = self.request.get('filter')
        if filterString:
            #Clever way to create the filters as generator expression
            return (self._convert_filter(kind, item) for item in filterString.split('&'))
        return ()   

    def _create_if_necessary(self, cls, currentEntity):
        default_properties = self.request.get('default');
        if not currentEntity and default_properties:
            #If the policy is to create an object if it doesn't already exist,
            #we should do that here
            initialValues = json.loads(default_properties)
            brandNewObj = cls(**initialValues)
            bnoKey = brandNewObj.put()
            if self.request.get('load') != 'all':
                currentEntity = [bnoKey]
            else:
                currentEntity = [brandNewObj]
        return currentEntity;
    
    def _convert_order(self, kind, property):
        match = re.match(r'^(?P<desc>-)?(?P<prop>.+)$', property)
        if not match:
            raise MalformedURLException("Something wrong with filter: %s" % (aFilter,))

        actualProp = getattr(kind, match.group('prop'))
        descending = match.group('desc');

        if descending:
            return -actualProp
        else:
            return actualProp
    
    def _get_order(self, cls):
        orderString = self.request.get('order')
        if orderString:        
            #Clever way to create the filters
            return (self._convert_order(cls, item) for item in orderString.split(','))
        return ()   

    def _perform_filter(self, cls):
        '''Performs a search for all items in a filter'''
                
        #=======================================================================
        # Create local variables for all the request variables
        #=======================================================================
        isLoadKeysOnly = self.request.get('load') != 'all'
        
        #Iterate through the responses. Implicitly fetches the results
        allItems =  cls.query(*self._get_filters(cls)).order(*self._get_order(cls)).fetch(keys_only=isLoadKeysOnly);
        
        #If the policy is to create an object if it doesn't already exist,
        #we should do that here
        return self._create_if_necessary(cls, allItems)

    def _write_all_objects_of_type(self, model_type):
        '''This finds all objects of a given type and writes them as a response'''
        allItems = self._perform_filter(getattr(model, model_type))
        
        #Write JSON back to the client
        self.response.headers['Content-Type'] = "application/json"
        self.response.write(parser.get_json_string(allItems))
        
    def _write_object_with_id(self, model_type, model_id):
        '''
        Writes an entity back to the client based on id. The value written will
        always be in JSON format. All filters will be ignored. It will by default 
        perform a load of all properties. Why else would you call this?
        '''

        #Simply get the object using NDB's class methods
        obj_result = [getattr(model, model_type).get_by_id(model_id)]

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