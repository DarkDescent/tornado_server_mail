# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

import json
import re
import unittest
import urllib

import os
from bson import ObjectId
from tornado.httpclient import AsyncHTTPClient
from tornado.testing import AsyncHTTPTestCase, gen_test

from rest_server import RestApplication

with open(os.path.join(os.path.dirname(__file__), "config/test.json"), mode="r") as fr:
  config = json.load(fr)
mongo_host = config["mongo_host"]
mongo_port = config["mongo_port"]
mongo_db_name = config["mongo_db_name"]
server_host = config["server_host"]
server_port = config["server_port"]

app = RestApplication(mongo_host, mongo_port, mongo_db_name)
objectid_re = re.compile("^[a-fA-F0-9]{24}$")

class BaseHTTPTestCase(AsyncHTTPTestCase):
  def setUp(self):
    super(BaseHTTPTestCase, self).setUp()
    self.http_client = AsyncHTTPClient(self.io_loop)

  def get_app(self):
    return app

  def tearDown(self):
    super(BaseHTTPTestCase, self).tearDown()
    self.db.drop_collection("users")
    self.db.drop_collection("posts")
    self.db.drop_collection("comments")

  @property
  def db(self):
    return self.get_app().motor


class MainHTTPTestCase(BaseHTTPTestCase):
  def is_objectid(self, obj):
    if isinstance(obj, ObjectId):
      return True
    if not isinstance(obj, basestring):
      return False
    return objectid_re.match(obj)

  def test_user_create(self):
    params = urllib.urlencode(dict(username="test123"))
    url = self.get_url("/user/create")
    response = self.fetch(url, method="POST", body=params)
    self.assertTrue(response.code == 200)
    self.assertTrue(self.is_objectid(response.body))

  @gen_test(timeout=10)
  def test_post_create(self):
    r = yield self.db.users.insert({"username": "test_post"})
    url = self.get_url('/post/create_post')
    params = urllib.urlencode(dict(user=r, tags="test", text="There is some test", title="Test"))
    response = yield self.http_client.fetch(url, method="POST", body=params)
    self.assertTrue(self.is_objectid(response.body))

if __name__ == "main":
  unittest.main()
