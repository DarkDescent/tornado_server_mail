# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

import logging

from bson import ObjectId
from tornado import gen
from tornado.web import asynchronous, HTTPError

from handlers.base_handler import BaseHandler
from utils.data_utils import now_aware, tolist, todate

logger = logging.getLogger(__name__)

class PostHandler(BaseHandler):
  """
  Хэндлер отвечает за создание и отображение поста, создание и отображение комментариев к посту, а также запрет
  пользователю оставлять комментарии под отдельным постом
  /post
  """

  @asynchronous
  @gen.coroutine
  def create_post(self):
    """
    Метод создает пост, используя следующие данные, которые должны быть переданы в запросе:
    1) user - _id пользователя
    2) tags - набор тегов данного поста
    3) text - текст поста
    4) title - заголовок поста

    :return: _id созданного документа в БД (в случае успеха)
    """
    user = self.get_argument("user")
    tags = self.get_argument_json("tags", [])
    text = self.get_argument("text", u"")
    title = self.get_argument("title")
    post_date = now_aware()
    r = yield self.motor.posts.insert({"user_id": ObjectId(user),
                                           "tags": tags,
                                           "text": text,
                                           "title": title,
                                           "post_date": post_date,
                                           "forbidden_for": []
                                           })
    self.finish(str(r))

  @gen.coroutine
  def _check_forbid_status(self, user_id, post_id):
    """
    Функция проверяет, может ли пользователь с идентификатором user_id оставлять сообщения в посте post_id

    :param user_id: идентификатор пользователя
    :param post_id: идентификатор поста
    :return: True, если пользователь не может оставлять комментарии, иначе False
    """
    post = yield self.motor.posts.find_one({"_id": ObjectId(post_id)})
    if user_id in post.get("forbidden_for") or []:
      raise gen.Return(True)
    raise gen.Return(False)

  @asynchronous
  @gen.coroutine
  def create_comment(self):
    """
    Метод создает комментарий к посту. Используются следующие данные:
      1) user - _id пользователя
      2) text - текст комментария
      3) post_id - идентификатор поста, к которому пишут комментарий

    :return: _id созданного документа
    """
    user = self.get_argument("user")
    text = self.get_argument("text")
    post_id = ObjectId(self.get_argument("post_id"))
    comment_date = now_aware()
    is_forbid = yield self._check_forbid_status(user, post_id)
    if is_forbid:
      raise HTTPError(503, "Forbid to send comments in this post")
    r = yield self.motor.comments.insert({
      "user_id": ObjectId(user),
      "text": text,
      "post_id": ObjectId(post_id),
      "comment_date": comment_date
    })
    self.finish(str(r))

  @asynchronous
  @gen.coroutine
  def forbid_user(self):
    """
    Метод указывает в информации о посте (post_id) пользователей, переданных в параметре запроса users, которые не будут
    иметь прав писать комментарии.

    :return: количество пользователей, переданных в users
    """
    users = self.get_argument_json("users", [])
    post_id = self.get_argument("post_id")
    yield self.motor.posts.update({"_id": ObjectId(post_id)}, {"$push": {"forbidden_for": {"$each": tolist(users)}}})
    self.finish(str(len(tolist(users))))


  @asynchronous
  @gen.coroutine
  def get_post(self):
    """
    Метод по post_id (передаваемому в параметрах) получает пост из БД и меняет (при возможности) идентификатор
    пользователя на его имя

    :return:
    """
    post_id = self.get_argument("post_id")
    post = yield self.motor.posts.find_one({"_id": ObjectId(post_id)})
    if not post:
      raise HTTPError(404, "There is no post with this _id")
    if "user_id" in post:
      user_id = post.pop("user_id")
      user = yield self.get_user_by_id(user_id) or {}
      post["username"] = user.get("username", u"")
    self.write_json(post)

  @gen.coroutine
  def _get_comments(self, query, sort, skip=0, limit=10):
    """
    Метод запрашивает данные из MongoDB.

    :param query: запрос в виде словаря, который поддерживается MongoDB.
    :param sort: информация о сортировке в формате MongoDB
    :param skip: сколько документов нужно предварительно пропустить (пагинация)
    :param limit: сколько всего документов показывать (пагинация)
    :return: документы - результат запроса
    """
    r = self.motor.comments.find(query).sort(sort.items()).limit(limit).skip(skip)
    docs = yield r.to_list(limit)
    # получаем данные по пользователям, чтобы вернуть в запросе их имена
    users = yield self.get_users_by_id([doc["user_id"] for doc in docs])
    for doc in docs:
      doc.pop("post_id")
      user_id = doc.pop("user_id")
      if user_id in users:
        doc["username"] = users[user_id]["username"]
      if "comment_date" in doc:
        doc["comment_date"] = todate(doc["comment_date"])
    raise gen.Return(docs)

  @asynchronous
  @gen.coroutine
  def get_comments(self):
    post_id = self.get_argument("post_id")
    sorting = int(self.get_argument("sorting", -1))
    skip = int(self.get_argument("skip", 0))
    limit = int(self.get_argument("limit", 10))
    query = {"post_id": ObjectId(post_id)}
    sorting = {"comment_date": sorting} if sorting else {}
    comments = yield self._get_comments(query, sorting, skip=skip, limit=limit)
    self.write_json(comments)

  def post(self, _type):
    types = {
      "create_post": self.create_post,
      "create_comment": self.create_comment,
      "forbid_user": self.forbid_user
    }
    if types.get(_type):
      types.get(_type)()
    else:
      raise HTTPError(404)

  def get(self, _type):
    types = {
      "get_post": self.get_post,
      "get_comments": self.get_comments,
    }
    if types.get(_type):
      types.get(_type)()
    else:
      raise HTTPError(404)
