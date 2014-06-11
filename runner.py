#!/usr/bin/env python
import gevent
from bot import Bot, Config

bot = Bot
config = Config('config.py').config
settings = config.SETTINGS

jobs = [gevent.spawn(bot, settings)]

try:
    gevent.joinall(jobs)
finally:
    gevent.killall(jobs)
