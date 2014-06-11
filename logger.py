#!/usr/bin/env python
#coding:utf-8

__author__ = 'York Wong'
__email__ = 'eth2net [at] gmail.com'
__date__ = '2013/01/30'

import logging


class Logger(object):
    def __init__(self):
        logging.basicConfig(
            level=logging.DEBUG,
            filename="./irc.log",
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filemode='a'
        )
        self.logger = logging.getLogger('irc')
#logger.setLevel(logging.DEBUG)
#ch = logging.StreamHandler()
#ch.setLevel(logging.DEBUG)
#formatter = \
    #logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#ch.setFormatter(formatter)
#logger.addHandler(ch)

    def log(self, func):
        def wrap(*args, **kwargs):
            self.logger.debug("%s %s" % (__file__, func.__name__))
            return func(*args, **kwargs)
        return wrap
