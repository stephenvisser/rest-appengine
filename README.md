# REST API for App Engine

A reusable REST API for GAE. See the __[most recent version LIVE](http://rest-dashboard-demo.appspot.com/)__

### Posting Data

-----------

    POST /api
    
Parameters | Possible Values
------|-------
DATA | Data must be of Content-Type: `application/json`. If we want to upload Blobs of data, see below for more information

__RETURNS:__ A string representing the long integer ID of the resource that was just uploaded

__Note:__ JSON objects uploaded to the server must contain a special `__type` property which specifies the server class with which it is associated. See below for a description of the different types.

__Note:__ JSON objects uploaded to the server _can_ contain an `__id` property; if set, the object will be set to the given ID, potentially overwriting any existing items

__Note:__ Nesting objects when posting is supported.

### Retrieving Data

-----------

    GET /api/<TYPE>/<ID>
    
Parameters | Possible Values
-----------|-------
TYPE       | One of the type objects listed below. Equivalent to the value of the `__type` property
ID         | The ID of the object we are interested in. Equivalent to the value of the `__id` property

__RETURNS:__ An array of JSON objects matching the criteria.  (Content-Type: `application/json`) representing the desired objects.  All internal objects will not be loaded -- they will be references to other .

__Note:__ An array is returned even if you specify the path to an object completely. This is so that data parsers on the client-side can function consistently.

__Note:__ If no Type is specified, all objects in the DB will be returned.

__Note:__ If the `__id` isn't specified, then all the values of type `__type` are returned. We can be even more specific by filtering adding the syntax: 
    
    ?filter=<PROPERTY_NAME><OPERATOR><VALUE>(<AND_SYMBOL><PROPERTY_NAME><OPERATOR><VALUE>)
    
Parameters | Possible Values
-----------|-------
PROPERTY_NAME | The name of the property. 
VALUE      | If the `__type` of this property object isn't simple, then this value must be the numerical `__id`. Otherwise, this value must be the value of the primitive type to compare to.
OPERATOR   | Can be one of `==`, `!=`, `>`, `<`, `>=`, `<=`

__Note:__ Multiple filters can be chained together by simply having multiple filter attributes

__Note:__ Currently the only supported property types are integers, strings and reference types (where the ID of the object is specified) 

    ?default=JSON_OBJ
    
Parameters | Possible Values
-----------|-------
JSON_OBJ | Must be formatted as a JSON object. This means curly brackets and quoted keys. The values included in the dictionary will populate the object.

__Note:__ If we are filtering on an object but it doesn't exist, we can use this to set its default values. It does nothing when the object is fully specified or when doing a classless search.

    ?load=<VALUE>
    
Parameters | Possible Values
-----------|-------
VALUE | Default is `none` where only the `__type` and `__id` properties are present. If `all`, we will return the object with all of its properties


### Deleting Data

-----------

    DELETE /api/<TYPE>/<ID>

Parameters | Possible Values
-----------|-------
TYPE       | One of the type objects listed below. Equivalent to the value of the `__type` property
ID         | The ID of the object we are interested in. Equivalent to the value of the `__id` property

    ?propagate=<CHILD_PROP>
    
Parameters | Possible Values
-----------|-------
CHILD_PROP | The name of the property we should propogate the DELETE to. Currently only do this for a single property

    ?force=<VALUE>

Parameters | Possible Values
-----------|-------
VALUE | Can be `yes` or `no`. The default is `no`

__RETURNS:__ Currently nothing will be returned

__Note:__ The force value is only used when users are deleting multiple values (they don't have the ID). This is to avoid mistakes being made and deleting entire tables

__Note:__ If neither of these parameters are given, all entities will be removed from the DB. This is useful for testing, but will likely be removed in subsequent versions

__Note:__ If only the type parameter is given, all entities of that type will be removed

__Note:__ If an object is fully-specified, that object will be removed

### PUT

---------------

__Note:__ Put is not supported. Since creating an object is not [indempotent](http://en.wikipedia.org/wiki/Idempotent) using our current API, we will not support this. See [this](http://stackoverflow.com/questions/630453/put-vs-post-in-rest) for a discussion of which (or both) people tend to support

# Dashboard

The REST API also has a useful dashboard which can be used to view which Objects exist.

## Model

The model is defined in the `/dashboard/model.py` file. 

## Viewing / Searching

Use the box in the upper-left corner. You just specify the URL of interest. Some examples:

    ?load=all
    
This will load all existing elements in the DB

    /User?filter=twitterHandle%3d%3dBOBBY&default={"twitterHandle":"abc123"}
    
This creates a User if the filter isn't satisfied using the entries in the JSON object as initial values

## Creating new objects

The text box in the bottom left can be used to create new objects. Just enter the name of the model object you want to create (e.g. `Entry`). Once it is created, use the right-most panel to enter properties by key name and value.

## Uploading files

There are a few special keywords in the property value field. The one of most interest is `file` When you press enter, you can drag and drop a file of interest which will be automatically uploaded to the server.

__TODO:__ Since this is a WIP, I haven't implemented error handling. If things break, the user interface won't tell you what happened.