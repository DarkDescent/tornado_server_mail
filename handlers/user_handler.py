# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'
import re
from tornado import gen
from tornado.web import HTTPError, asynchronous

from handlers.base_handler import BaseHandler

username_rule = re.compile(ur"[A-Za-z0-9]+")

class UserHandler(BaseHandler):
  """
  Хэндлер отвечает за создание и редактирование (задание прав) пользователей в системе
  /user
  """

  @gen.coroutine
  def _create_user(self, username):
    """
    Функция создает пользователя, сохраняя его в базе

    :param username: имя пользователя
    :return: _id пользователя
    """
    if not username_rule.match(username):
      raise HTTPError(400, "Username must contain only latin characters and numbers")

    is_exist = yield self.check_if_user_exists(username)
    if is_exist:
      raise HTTPError(400, "Username already used")
    r = yield self.motor.users.insert({"username": username})
    raise gen.Return(str(r))

  @asynchronous
  @gen.coroutine
  def create_user(self):
    """
    Функция создает пользователя, сохраняя его в базе

    :return: _id пользователя
    """
    r = yield self._create_user(self.get_argument("username"))
    self.finish(r)

  def post(self, _type):
    types = {
      "create": self.create_user,
    }
    if types.get(_type):
      types.get(_type)()
    else:
      raise HTTPError(404)
