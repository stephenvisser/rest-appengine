'''
This is the main package for REST API code.
We must also load the model class from the Caller's settings
'''

from appengine_config import model_settings
model = __import__(model_settings['path'])