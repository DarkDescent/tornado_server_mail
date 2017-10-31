# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

import re
from datetime import datetime
from dateutil.tz import tzlocal, tzutc
from dateutil.parser import parse

"""
Модуль содержит все дополнительные методы, необходимые для работы сервера
"""

_retype = type(re.compile(''))

def custom_handler(obj):
  """
  Специальный метод для параметра default метода json.dumps

  :param obj: объект, к которому нужно применить определенное изменение (в завимости от типа)
  :return: преобразованний к нужному формату obj
  """
  if hasattr(obj, 'isoformat') and callable(getattr(obj, 'isoformat')):
    return obj.isoformat()
  if obj.__class__.__name__ == "ObjectId":
    return str(obj)
  if obj.__class__ is set:
    return list(obj)
  if obj.__class__ is _retype:
    return obj.pattern
  return None

def now_aware():
  """
  Метод получает текущее время и приводит его к текущей локали

  :return: текущее время вместе с временной зоной
  """
  return datetime.now().replace(microsecond=0)
  # return datetime.now(tzlocal()).replace(microsecond=0)


def todate(obj):
  """
  Метод пытается превратить значение obj в datetime (в правильной временной зоне)

  :param obj: значение, которое необходимо перевести в datetime
  :return: obj, если преобразование невозможно, иначе datetime
  """
  if not obj:
    return None
  res = None
  if obj.__class__ is datetime:
    res = obj
  if obj.__class__ in (str, unicode):
    try:
      res = parse(obj, dayfirst=True, yearfirst=True)
    except Exception:
      pass
  if obj.__class__ in (int, long, float):
    try:
      res = datetime.fromtimestamp(obj)
    except Exception:
      pass
  # if res.__class__ is datetime:
  #     res = res.replace(tzinfo=tzlocal())
  #     res = res.replace(microsecond=0)

  return res


def tolist(obj):
  """
  Метод пытается преобразовать переменную в список (если представлен объект, по которому можно итерироваться,
  преобразуем его в list, иначе делаем [obj])

  :param obj: значение, которое надо преобразовать в список
  :return: obj как список
  """
  if obj is None:
    return []
  if hasattr(obj, "__iter__"):
    return list(obj)
  return [obj]
