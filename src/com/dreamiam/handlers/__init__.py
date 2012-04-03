import webapp2
from com.dreamiam.handlers.rest_api import Rest

app = webapp2.WSGIApplication([('/api.*', Rest)], debug=True)
