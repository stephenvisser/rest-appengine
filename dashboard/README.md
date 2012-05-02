# Dashboard

-----

This project is for GAE and allows users to easily manage and search the DB.

I don't want to give too much away (it should be self-documenting), but there are several keywords which you can use when creating values. One of the most interesting is `file` which will allow you to upload anything you like to the server and then view it. Best if it is a sound or image.

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
