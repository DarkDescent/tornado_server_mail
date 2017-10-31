# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

import re
import logging

from bson import ObjectId
from tornado import gen
from tornado.web import asynchronous, HTTPError

from handlers.base_handler import BaseHandler
from utils.data_utils import tolist, todate

logger = logging.getLogger(__name__)

class PostsHandler(BaseHandler):
  """
  Хэндлер отвечает за получение постов пользователей (с применением фильтров, сортировок)
  /posts
  """
  @gen.coroutine
  def _get_posts(self, query, sort, skip=0, limit=10):
    """
    Метод запрашивает данные из MongoDB.

    :param query: запрос в виде словаря, который поддерживается MongoDB.
    :param sort: информация о сортировке в формате MongoDB
    :param skip: сколько документов нужно предварительно пропустить (пагинация)
    :param limit: сколько всего документов показывать (пагинация)
    :return: документы - результат запроса
    """
    r = self.motor.posts.find(query).sort(sort.items()).limit(limit).skip(skip)
    docs = yield r.to_list(limit)
    # получаем данные по пользователям, чтобы вернуть в запросе их имена
    users = yield self.get_users_by_id([doc["user_id"] for doc in docs])
    for doc in docs:
      user_id = doc.pop("user_id")
      if user_id in users:
        doc["username"] = users[user_id]["username"]
      if "post_date" in doc:
        doc["post_date"] = todate(doc["post_date"])
    raise gen.Return(docs)

  @asynchronous
  @gen.coroutine
  def get_posts_by_user(self):
    """
    Метод получает _id пользователя (user), а также настройки сортировки даты публикации:
      -1 по убыванию
      1 - по возрастанию
      0 (или не присылать) - без сортировки

    :return: список документов пользователя, при указании отсортированные
    """
    user = self.get_argument("user")
    sorting = int(self.get_argument("sorting", -1))
    skip = int(self.get_argument("skip", 0))
    limit = int(self.get_argument("length", 10))
    sorting = {"post_date": sorting} if sorting else {}
    query = {"user_id": ObjectId(user)}
    docs = yield self._get_posts(query, sorting, skip=skip, limit=limit)
    self.write_json(docs)

  @asynchronous
  @gen.coroutine
  def get_posts(self):
    """
    Метод запрашивает данные по постам пользователей. Используются следующие фильтры:
      tags - набор тегов
      min_date - минимальная дата публикации
      max_date - максимальная дата публикации
      title - слово или словосочетание, которое надо искать в заголовках постов
    Настройки сортировки по дате публикации:
      -1 по убыванию
      1 - по возрастанию
      0 (или не присылать) - без сортировки

    :return: список документов по запросу, при указании отфильтрованные
    """
    tags = self.get_argument_json("tags", [])
    min_date = self.get_argument("min_date", None)
    max_date = self.get_argument("max_date", None)
    title_query = self.get_argument("title", "")
    sorting = int(self.get_argument_json("sorting", -1))
    skip = int(self.get_argument("skip", 0))
    limit = int(self.get_argument("length", 10))

    query = {}
    if tags:
      query["tags"] = {"$in": tolist(tags)}
    query_date = {}
    if min_date:
      query_date["$gte"] = todate(min_date)
    if max_date:
      query_date["$lte"] = todate(max_date)
    if query_date:
      query["post_date"] = query_date
    if title_query:
      query["title"] = re.compile(u"%s" % re.escape(title_query), re.IGNORECASE)

    sorting = {"post_date": sorting} if sorting else {}
    docs = yield self._get_posts(query, sorting, skip=skip, limit=limit)
    self.write_json(docs)

  def get(self, _type):
    types = {
      "by_user": self.get_posts_by_user,
      "posts": self.get_posts
    }
    if types.get(_type):
      types.get(_type)()
    else:
      raise HTTPError(404)
