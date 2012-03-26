# Dream Cache App
The app allows users to record their dreams.

### Live Tag Search

-----------

    GET /query/<SEARCH_STRING>
    
Parameters | Possible Values
------|-------
SEARCH_STRING | Leave empty and will return all strings, otherwise, will return all strings that start with the given string

__RETURNS:__ A list of strings (Content-Type: `application/json`) which match the query

### Posting Data

-----------

    POST /api
    
Parameters | Possible Values
------|-------
DATA | Data can be either of Content-Type: `application/json` or `multipart/form-data`

__RETURNS:__ The numeric ID of the resource that was just uploaded

__Note:__ When the Content-Type is `multipart/form-data`, the first part message can have whatever name it likes. Convention is `name=ROOT`. This first part will be parsed as a JSON object and all other entities will appended to this root object as deferred objects which will require seperate `GET` requests. 

__Note:__ JSON objects uploaded to the server must contain a special `__type` property which specifies the server class with which it is associated. See below for a description of the different types.

__Note:__ Notifications should be sent to all clients when the data being posted is an Entry. The device that created the entry shouldn't receive any notification and should be responsible for doing its own local notification.

__Note:__ When an object already exists and needs to be changed, it will simply be overwritten. Notifications will be sent to all clients that the entry has been added. All clients should therefore ensure that the object isn't already represented.

### Retrieving Data

-----------

    GET /api/<TYPE>/<ID>
    
Parameters | Possible Values
-----------|-------
TYPE       | One of the type objects listed below. Equivalent to the value of the `__type` property
ID         | The ID of the object we are interested in. Equivalent to the value of the `__id` property

__RETURNS:__ A JSON object (Content-Type: `application/json`) representing the desired objects.  All sub-objects aside from `Data` objects will be loaded also.

__Note:__ If the `__id` isn't specified, then all the values of type `__type` are returned. We can be even more specific by filtering adding the syntax: 
    
    ?filter=<PROPERTY_NAME>:<VALUE>
    
Parameters | Possible Values
-----------|-------
PROPERTY_NAME | The name of the property. 
VALUE      | If the `__type` of this property object isn't simple, then this value must be the numerical `__id`. Otherwise, this valu must be the value of the primitive type to compare to.

__Note:__ Currently only possible to filter on one value at a time

__Note:__ Currently the only supported property types are integers, strings and reference types (where the ID of the object is specified) 

    ?non_exist=<VALUE>
    
Parameters | Possible Values
-----------|-------
VALUE | Default is `fail`. If `create`, we will create a new object with the given filters if the object doesn't exist.

__Note:__ Best used in conjunction with a filter since it uses filter value to populate the new object

    ?load_content=<VALUE>
    
Parameters | Possible Values
-----------|-------
VALUE | Default is `none` where only the `__type` and `__id` properties are present. If `all`, we will return the object with all of its properties

__Note:__ In cases where the path to an object is completely specified, this defaults to `all` because it is redundant otherwise. However, in all other cases where some ambiguity as to the identity of the object, the default is `none`.

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

__Note:__ Notifications should be sent to all clients when the data being deleted is an Entry. The device that deleted the entry shouldn't receive any notification and should be responsible for doing its own local notification.

__Note:__ If neither of these parameters are given, all entities will be removed from the DB. This is useful for testing, but will likely be removed in subsequent versions

__Note:__ If only the type parameter is given, all entities of that type will be removed

__Note:__ If an object is fully-specified, that object will be removed

### PUT

---------------

__Note:__ Put is not supported. Since creating an object is not [indempotent](http://en.wikipedia.org/wiki/Idempotent) using our current API, we will not support this. See [this](http://stackoverflow.com/questions/630453/put-vs-post-in-rest) for a discussion of which (or both) people tend to support

### Types

#### Entry
-------
Property | Description
---------|-------
__id     | Uniquely identifies the object
__type   | (__REQUIRED__) `Entry`
user     | (__REQUIRED__) The `User` object (see below)
tags     | A list of string tags that the entry has associated with it
location | The `Location` object for where the dream was recorded
timestamp| A integer number representing the time in seconds since 1970 from when recording began and is used in the filesystem to uniquely identify the recordings
deviceToken | A token which identifies the device which was used to record the entry.
sound    | This is the binary form of the recording made by the user. Stored in a `Data` object with Content-Type `audio/mp4`

#### User
-------
Property  | Description
------|-------
__id     | Uniquely identifies the object
__type   | (__REQUIRED__) `User`
twitterHandle | (__REQUIRED__) the twitter username they have
devices  | An array of all the devices that have been used to record dreams

#### Location
-------
Property  | Description
------|-------
__id     | Uniquely identifies the object
__type   | (__REQUIRED__) `GeoPt`
lat| (__REQUIRED__) Latitude (floating point)
lon | (__REQUIRED__) Longitude (floating point)

#### Data
-------
Property  | Description
------|-------
__id     | Uniquely identifies the object
__type   | (__REQUIRED__) `Data`
__contentType | String representing the HTTP `Content-Type` that was used to upload this information. Server-side only. Use the URL property to retrieve the binary data
__data   | Binary data that constitudes the data object. Server-side only. Use the URL property to retrieve the binary data

 __Note:__ When referencing objects, the `__type` property is always required. If the `__id` is specified, all other properties are ignored and the object is simply referenced.
 
 
### Notifications

---------

The `userInfo` dictionary contains the following:

Key   | Value
----- |-------
__id  | The ID of the object being changed
__type| The type of the object being changed

__Note:__ In addition, remote notifications will have the additional `action` parameter which can be either `"add"` or `"remove"`.

