# -*- coding: utf-8 -*-
__author__ = 'vatyakshin'

# import sys
#
# reload(sys)
# sys.setdefaultencoding("utf-8")

import logging
import sys
from logging.handlers import RotatingFileHandler

from motor import MotorClient
from os import makedirs
from os.path import exists, dirname, expandvars
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop
from tornado.options import define, options
from tornado.web import Application

from handlers.post_handler import PostHandler
from handlers.posts_handler import PostsHandler
from handlers.user_handler import UserHandler

logger = logging.getLogger(__name__)


class RestApplication(Application):
  """
  Класс-наследник tornado Application. Настраивает хэндлеры проекта, путь до шаблонов и css, а также создает объект
  MotorClient и сохраняет его в свой атрибут
  """
  def __init__(self, mongo_host, mongo_port, mongo_db_name, tornado_debug=None):
    """
    Инициализация класса
    """
    handlers = [
      (r"/user/(.*)", UserHandler),
      (r"/post/(.*)", PostHandler),
      (r"/posts/(.*)", PostsHandler)
    ]
    settings = dict(
      title="Test Mail",
      debug=tornado_debug or True,
    )
    super(RestApplication, self).__init__(handlers, **settings)
    motor = MotorClient(mongo_host, mongo_port, tz_aware=True)
    self.motor = motor[mongo_db_name]


if __name__ == "__main__":
  define("c", default="config/server.conf", help="server configuration")
  define("server_host", default="127.0.0.1", help="server host")
  define("server_port", default=8080, help="server port", type=int)
  define("logpath", default="", help="path to log file")
  define("logformat", default="%(asctime)s - %(levelname)s - %(message)s", help="format of log entries")
  define("loglevel", default="INFO", help="logging level")
  define("mongo_host", default="127.0.0.1", help="mongodb host")
  define("mongo_port", default=27017, help="mongodb port", type=int)
  define("mongo_db_name", default="", help="mongodb database name")
  define("debug", default=True, help="debug mode", type=bool)

  options.parse_command_line()
  configpath = expandvars(options.c)
  options.parse_config_file(configpath)
  options.parse_command_line()

  # init logging subsystem
  logfile = expandvars(options.logpath)
  log_dir = dirname(logfile)
  if log_dir and not exists(log_dir):
    makedirs(log_dir)

  # clear logging
  root = logging.getLogger()
  for handler in root.handlers or []:
    root.removeHandler(handler)

  logging.basicConfig(filename=logfile, level=logging.getLevelName(options.loglevel or "INFO"),
                      format=options.logformat, filemode="w")
  rfh = RotatingFileHandler(logfile, mode='a', maxBytes=1024 * 1024 * 2, backupCount=1, encoding="utf8")
  logging.getLogger().addHandler(rfh)

  application = None

  try:
    application = RestApplication(options.mongo_host, options.mongo_port, options.mongo_db_name, options.debug)
  except Exception as e:
    logger.exception(e)
    sys.exit(1)

  AsyncHTTPClient.configure(CurlAsyncHTTPClient, max_clients=50)
  application.listen(options.server_port, address=options.server_host, max_buffer_size=200000000000)
  logging.info("rest server started on %s" % options.server_port)
  print "rest server started on %s" % options.server_port
  IOLoop.instance().start()
