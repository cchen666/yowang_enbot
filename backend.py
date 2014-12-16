#!/usr/bin/env python
#coding:utf-8

__author__ = 'York Wong'
__email__ = 'eth2net [at] gmail.com'
__date__ = '2012/11/07'

import gevent
import gevent.monkey
from gevent import queue
gevent.monkey.patch_all()

import os
import sys
import re
import getpass
import socket
from datetime import datetime

from pymongo.errors import DuplicateKeyError

import urllib
import mechanize

from pyquery import PyQuery as pq

import select

from db import get_collection
import config

#config
contry_pattern = r"Identifying Address Country: (.+) \((\d+) record|s\)"
conf = config.Config()
REPORT_NEWCASE = conf.SETTINGS['report']['new_case']
REPORT_ESCALATION = conf.SETTINGS['report']['escalation']
REPORT_NCQ = conf.SETTINGS['report']['ncq']
SBR_MSG=''


# Reuse monitor code
class FakeBrowser(object):
    def __init__(self, username, password, cookie_file, debug=False):
        self.username = username
        self.password = password
        self.cookie_file = cookie_file
        self.debug = debug
        self.user_agent = ('Mozilla/5.0 (X11; Linux x86_64; rv:8.0.1) Gecko/20100101 Firefox/8.0.1')
        self.browser = None

    def get_browser(self):
        """Browser object response for load cookie and save cookie"""
        if self.browser:
            return self.browser
        else:
            browser = mechanize.UserAgent()
            browser.set_handle_equiv(False)
            browser.set_handle_gzip(False)
            browser.set_handle_redirect(True)
            browser.set_handle_robots(False)
            browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
            browser.set_seekable_responses(False)
            if self.debug:
                browser.set_debug_http(True)
                browser.set_debug_redirects(True)
                browser.set_debug_responses(True)
            cj = mechanize.LWPCookieJar()
            try:
                cj.load(self.cookie_file, ignore_discard=True, ignore_expires=True)
            except IOError:
                pass
            browser.set_cookiejar(cj)
            browser.addheaders = [
                ('User-agent', self.user_agent),
            ]
            self.browser = browser
            return self.browser

    def get_cookie_string(self, url):
        """Get cookie string for a given url"""
        br = self.get_browser()
        r = mechanize.Request(url)
        cookies = br._ua_handlers['_cookies'].cookiejar.cookies_for_request(r)
        attrs = br._ua_handlers['_cookies'].cookiejar._cookie_attrs(cookies)
        return "; ".join(attrs)

    def request(self, url, data=None):
        """Request a page from xunlei"""
        br = self.get_browser()
        br.addheaders.append(('Referer', 'http://na7.salesforce.com'))
        if data:
            data = urllib.urlencode(data)
        response = br.open(url, data)
        br._ua_handlers['_cookies'].cookiejar.save(self.cookie_file, ignore_discard=True, ignore_expires=True)
        return response

    def login(self):
        #br = self.get_browser()
        self.get_browser()
        data = {
            'un': self.username,
            'username': self.username,
            'hasRememberUn': True,
            'pw': self.password,
            'rememberUn': 'on',
            'Login': 'Login',
            'display': 'page',
            'lt': 'standard',
        }
        response = self.request('http://login.salesforce.com/', data)
        return response

    def runreport(self, url_report):
        report = self.request(url_report).read()
        return report


def report_parser(html_source):

    """
    Give the HTML code to pyquery
    decode to unicode before given to pyquery, it would solve underlaying CJK encoding issue.
    Check pyquery doc for details to parse your report: http://packages.python.org/pyquery/
    """

    report = pq(html_source.decode("utf-8"))

    table = report("table.reportTable.tabularReportTable")

    trs = table("tr")
    lens = len(trs)

    current_case_list = []
    prev_case_list = []

    p = get_collection('cases')

    for i in xrange(0, lens):
        if trs.eq(i).hasClass("breakRowClass1.breakRowClass1Top"):
            res = re.search(contry_pattern, trs.eq(i).text())
            if res:
                region = res.group(1)
                record = res.group(2)

                if region.startswith("Hong"):
                    region = 'HK'
                elif region.startswith("Tai"):
                    region = 'TW'
                elif region.startswith("Kor"):
                    region = 'KR'
                elif region.startswith("Chin"):
                    region = 'CN'
                else:
                    region = 'Global'

            for k in xrange(i + 1, i + int(record) + 2):
                if trs.eq(k).hasClass("even"):
                    case = {}
                    tds = trs.eq(k)("td")

                    # for testing purpose and get the fields and filed seq number
                    #for i in xrange(len(tds)):
                        #print "%s: %s" % (i, tds.eq(i).text())

                    case['_id'] = tds.eq(2).text()
                    case['owner'] = tds.eq(1).text()
                    case['subject'] = tds.eq(3).text()
                    case['sbt'] = tds.eq(4).text()
                    case['severity'] = tds.eq(5).text()[0]
		    if tds.eq(14).text() == "-":
		
			    case['sbr'] = "No SBR"
		    else:
			case['sbr'] = tds.eq(14).text()
                    status = tds.eq(6).text().strip()
                    if status == 'Waiting on Red Hat':
                        case['status'] = 'WoRH'
                    elif status == 'Waiting on Customer':
                        case['status'] = 'WoCU'
                    else:
                        case['status'] = status
                    case['mute'] = False
                    case['inter_stat'] = tds.eq(7).text()
                    case['nno'] = True if tds.eq(8).text() == 'Any' else False
                    case['account'] = tds.eq(11).text()
                    case['region'] = region
                    case['has_owner'] = True if case['nno'] else False
                    case['url'] = 'https://na7.salesforce.com' + tds.eq(3)("a").attr("href")

                    current_case_list.append(case['_id'])
                    res = p.find_one({'_id': case['_id']})

                    if res:
                        #continue
                        case['mute'] = res['mute']
                        try:
                            p.update({'_id': case['_id']}, case)
                        except:
                            print 'Unexpected error:', sys.exc_info()[0]
                    else:
                        #case['owner'] = tds.eq(1).text()
                        #case['subject'] = tds.eq(3).text()
                        #case['sbt'] = tds.eq(4).text()
                        #case['severity'] = tds.eq(5).text()[0]
                        #status = tds.eq(6).text().strip()
                        #if status == 'Waiting on Red Hat':
                            #case['status'] = 'WoRH'
                        #elif status == 'Waiting on Customer':
                            #case['status'] = 'WoCU'
                        #case['mute'] = False
                        #case['inter_stat'] = tds.eq(7).text()
                        #case['nno'] = True if tds.eq(8).text() == 'Any' else False
                        #case['account'] = tds.eq(11).text()
                        #case['region'] = region
                        #case['has_owner'] = True if case['nno'] else False
                        #case['url'] = 'https://na7.salesforce.com' + tds.eq(3)("a").attr("href")

                        try:
                            p.insert(case)
                        except DuplicateKeyError:
                            print "Case exist:", sys.exc_info()[0]
                        except:
                            print "Unexpected error:", sys.exc_info()[0]

    #Get cases in prev_case_list but not in current_case_list, mark them to has_owner, remove nno tag and unmute
    query_str = {'$or': [
                {'has_owner': False},
                {'nno': True},
    ]
    }
    #print current_case_list
    prev_case_list = map(lambda x: x.get('_id'), list(p.find(query_str, {'_id': 1})))
    #print prev_case_list
    taken_list = list(set(prev_case_list) - set(current_case_list))
    for _id in taken_list:
        p.update({'_id': _id}, {'$set': {'has_owner': True, 'nno': False, 'mute': False}})


def escalation_parser(html_source):

    """
    Give the HTML code to pyquery
    decode to unicode before given to pyquery, it would solve underlaying CJK encoding issue.
    Check pyquery doc for details to parse your report: http://packages.python.org/pyquery/
    """

    report = pq(html_source.decode("utf-8"))

    table = report("table.reportTable.tabularReportTable")

    trs = table("tr.even")

    current_case_list = []
    prev_case_list = []
    p = get_collection("escalation")

    for i in xrange(0, len(trs)):
        case = {}
        tds = trs.eq(i)("td")

        case['_id'] = tds.eq(3).text()
        res = p.find_one({'_id': case['_id']})
        if res:
            continue
        else:
            case['owner'] = tds.eq(1).text()
            case['account'] = tds.eq(2).text()
            case['subject'] = tds.eq(5).text()
            case['severity'] = tds.eq(8).text()
            case['url'] = 'https://na7.salesforce.com' + tds.eq(3)("a").attr("href")
            case['checked'] = False
            current_case_list.append(case['_id'])

            try:
                p.insert(case)
            except DuplicateKeyError:
                print 'Case exist:', sys.exc_info()[0]
                print case['_id']
            except:
                print 'Unexpected error:', sys.exc_info()[0]

    query_str = {'checked': False}
    prev_case_list = map(lambda x: x.get('_id'), list(p.find(query_str, {'_id': 1})))
    taken_list = list(set(prev_case_list) - set(current_case_list))
    for _id in taken_list:
        p.update({'_id': _id}, {'$set': {'checked': True}})

def ncq_parser(html_source):

    """
    Give the HTML code to pyquery
    decode to unicode before given to pyquery, it would solve underlaying CJK encoding issue.
    Check pyquery doc for details to parse your report: http://packages.python.org/pyquery/
    """

    global SBR_MSG

    sbr_dic={}

    report = pq(html_source.decode("utf-8"))

    table = report("table.reportTable.tabularReportTable")

    trs = table("tr")
    lens = len(trs)
    p = get_collection("ncq")


    for i in xrange(1, lens-2):
        key = trs.eq(i)("td").eq(6).text()
        if key == '-':
                key = "No_SBR"
        if not sbr_dic.has_key(key):
               sbr_dic[key] = 1
        elif sbr_dic.has_key(key):
               sbr_dic[key] += 1

    #print sbr_dic

    sbr_msg=''
    for key in sbr_dic.keys():
        sbr_msg += key
        sbr_msg += '  '
        sbr_msg += str(sbr_dic[key])
        sbr_msg += '  '
    sbr_msg = "Global NCQ SBR : " + sbr_msg
    SBR_MSG = sbr_msg
    p.update({'_id': 200}, {'$set': {'content': SBR_MSG}})

    #print "SBR_MSG in backend.py   " + SBR_MSG
    #self._say(self.settings['channels'][0],sbr_msg)

def get_sbr():
	global SBR_MSG
	return SBR_MSG


class Backend(object):

    #def __init__(self):
    def __init__(self, browser):
        self.browser = browser          # fake browser
        self.mqueue = queue.Queue()

    def report_thread(self):
        while True:
            if now.hour in xrange(9, 17) and now.isoweekday() in xrange(1, 6):
                #print 'Put to queue: Done'
                self.mqueue.put('Done')
                gevent.sleep(conf.SETTINGS['chk_interval'])
                report_parser(self.browser.runreport(REPORT_NEWCASE))
		ncq_parser(self.browser.runreport(REPORT_NCQ))
                #f = open("./report.html").read()
                gevent.sleep(2)
                escalation_parser(self.browser.runreport(REPORT_ESCALATION))

    def server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #In order to reuse the socket immediately after backend shutdown and restart
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	#print "Binding"
        server.bind(("127.0.0.1", 5050))
        #print "Binded"

        server.listen(1)

        readlist = [server]
        m = None

        while True:
            (sread, swrite, sexc) = select.select(readlist, [], readlist, 5)

            try:
                m = self.mqueue.get_nowait()
            except queue.Empty:
                if len(readlist) > 1:
                    m = 'has_client'

            for sock in readlist:
                if sock != server:
                    try:
                        if m == 'Done':
                            sock.send('Done\n')
                        elif m == 'has_client':
                            sock.send('keepalive\n')
                    except socket.error, e:
                        # [Errno 32] Broken pipe
                        if e.errno == 32:
                            readlist.remove(sock)
                            m = None
                            print 'Client disconnected'

            for sock in sread:
                if sock == server:
                    (newsock, address) = server.accept()
                    newsock.setblocking(0)
                    if len(readlist) < 2:
                        print "I got a connection from", address
                        readlist.append(newsock)
                        newsock.send("Accepted\n")
                    else:
                        newsock.send("Rejected\n")
                        newsock.close()
                else:
                    try:
                        d = sock.recv(10)
                        print d
                        if d == 'connected':
                            sock.send('Done\n')
                    except Exception, e:
                        print 'err:', e

    def run(self):
        print "Running backend instance"

        jobs = [
            gevent.spawn(self.server),
            gevent.spawn(self.report_thread),
        ]
        #print "Joining"

        gevent.joinall(jobs)

if __name__ == '__main__':
    #f = open("./report.html").read()

    #m = FakeBrowser(username='yowang@redhat.com', password=getpass.getpass("password: "), cookie_file="./.cookie")
    m = FakeBrowser(username=raw_input("Your SFDC username: "), password=getpass.getpass("Password: "), cookie_file="./.cookie")
    m.login()

    #m = None
    now = datetime.now()
    if now.hour in xrange(9, 17) and now.isoweekday() in xrange(1, 6):
        f = m.runreport(REPORT_NEWCASE)
        #report_parser(f)
        report_parser(f)
        f = m.runreport(REPORT_ESCALATION)
        escalation_parser(f)
	f = m.runreport(REPORT_NCQ)
	ncq_parser(f)
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError, e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)
    # decouple from parent environment
    #os.chdir("/")
    os.setsid()
    os.umask(0)
    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent, print eventual PID before
            print "Daemon PID %d" % pid
            #f = open("/var/run/enbot.pid", 'w')
            #f.write(str(pid))
            #f.close()
            sys.exit(0)
    except OSError, e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)
    
    backend = Backend(m)
    #backend = Backend()
    backend.run()
