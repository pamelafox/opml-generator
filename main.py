"""
 Licensed under the Apache License, Version 2.0:
 http://www.apache.org/licenses/LICENSE-2.0
"""

import os
import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from django.utils import simplejson


class BaseRequestHandler(webapp.RequestHandler):

  def get(self):
    page = memcache.get(self.get_cachename())
    if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
      page = None
    if not page:
      path = os.path.join(os.path.dirname(__file__), self.get_filename())
      page = template.render(path, self.get_values())
      memcache.set(self.get_cachename(), page, 60*1)
    self.response.headers['Content-Type'] = self.get_mimetype()
    self.response.out.write(page)

  def get_mimetype(self):
    return 'text/html'

class HomePage(BaseRequestHandler):

  def get_filename(self):
    return 'base.html'

  def get_cachename(self):
    return 'index'

  def get_values(self):
    return {}

class FeedOPML(BaseRequestHandler):

  def get_filename(self):
    return 'opml.xml'

  def get_cachename(self):
    return 'feedopml'

  def get_values(self):
    title = self.request.get('title', 'Custom OPML')
    return {'feeds': self.get_worksheet_data(), 'title': title}

  def get_mimetype(self):
    return 'application/atom+xml'

  def get_worksheet_data(self):
    spreadsheet_key = self.request.get('sskey')
    worksheet_id = self.request.get('wsid', 'od6')
    url = 'https://spreadsheets.google.com/feeds/list/%s/%s/public/values?alt=json' % (spreadsheet_key, worksheet_id)
    result = urlfetch.fetch(url)
    rows = []
    fields = ['title', 'url']
    if result.status_code == 200:
      json = simplejson.loads(result.content)
      feed = json['feed']
      entries = []
      if 'entry' in feed:
        entries = feed['entry']
      for entry in entries:
        row_info = {}
        dont_append = False
        for field in fields:
          if not entry['gsx$' + field] or len(entry['gsx$' + field]['$t']) == 0:
            dont_append = True
          row_info[field] = entry['gsx$' + field]['$t']
        if not dont_append:
          rows.append(row_info)
    return rows


application = webapp.WSGIApplication(
                                     [('/', HomePage),
                                      ('/opml', FeedOPML)],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()
