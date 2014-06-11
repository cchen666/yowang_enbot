#!/usr/bin/env python
#coding:utf-8

__author__ = 'York Wong'
__email__ = 'eth2net [at] gmail.com'
__date__ = '2013/01/27'

import pymongo
BOTDB = 'enbot'

def get_collection(collection):
    try:
        conn = pymongo.MongoClient("localhost", safe=True)
    except:
        print 'Unable to connect mongodb, exit...'
        sys.exit(0)
    db = conn[BOTDB]
    return db[collection]

if __name__=='__main__':
    p= get_collection('ncq')
    print p.find_one({'_id':200})['content']
    #pass

