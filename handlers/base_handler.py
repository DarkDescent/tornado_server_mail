# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

import json
import logging

from bson import ObjectId
from tornado import gen
from tornado.web import RequestHandler

from utils.data_utils import custom_handler, tolist

logger = logging.getLogger(__name__)

class BaseHandler(RequestHandler):
  """
  Класс является родительским классом для всех хэндлеров проекта.
  """
  @property
  def motor(self):
    """
    объект MotorClient, подключения к MongoDB

    :return:
    """
    return self.application.motor

  def get_argument_json(self, name, default=None):
    if default is None:
      argval = self.get_argument(name)
    else:
      argval = self.get_argument(name, default=default)
    if isinstance(argval, basestring):
      return json.loads(argval)
    return argval

  def write_json(self, results):
    self.set_header("Content-Type", "application/json; charset=UTF-8")
    self.finish(json.dumps(results, default=custom_handler, sort_keys=False))

  @gen.coroutine
  def check_if_user_exists(self, username):
    """
    Функция запрашивает базу на наличие персоны с именем username

    :param username:
    :return:
    """
    r = yield self.motor.users.find_one({"username": username})
    if not r:
      raise gen.Return(False)
    raise gen.Return(True)

  @gen.coroutine
  def get_users_by_id(self, user_id):
    """
    Функция возвращает информацию о пользователях из БД по их идентификаторам

    :param user_id: идентификаторы пользователей
    :return: информация о пользователях в формате bson
    """
    if not user_id:
      raise gen.Return([])
    r = self.motor.users.find({"_id": {"$in": [ObjectId(_id) for _id in tolist(user_id)]}})
    users = yield r.to_list(len(tolist(user_id)))
    raise gen.Return(dict(
      ((user["_id"], user) for user in users)
    ))

  @gen.coroutine
  def get_user_by_id(self, user_id):
    """
    Функция возвращает информацию о пользователе из БД по идентификатору.

    :param user_id: идентификатор пользователя
    :return: информация о пользователе в формате bson
    """
    if not user_id:
      raise gen.Return(None)
    r = yield self.motor.users.find_one({"_id": ObjectId(user_id)})
    raise gen.Return(r)
