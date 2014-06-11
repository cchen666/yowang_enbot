#from voxbot import irc
#from voxbot import loader
import irc
import loader

import sys
import os
import re
import imp
import string
from datetime import datetime

import gevent
from gevent import monkey
import socket
monkey.patch_all()
import commander
from db import get_collection
import backend

# Get from unified/src/com/redhat/gss/irc/irc_classes.py author: smendenh
BOLD      = "\x02"
COLOR     = "\x03"
CLEAR     = "\x0F"
ITALIC    = "\x10"  # I don't think this actually works...
UNDERLINE = "\x1F"
WHITE     = COLOR + "00"
BLACK     = COLOR + "01"
BLUE      = COLOR + "02"
GREEN     = COLOR + "03"
RED       = COLOR + "04"
BROWN     = COLOR + "05"
PURPLE    = COLOR + "06"
ORANGE    = COLOR + "07"
YELLOW    = COLOR + "08"
LT_GREEN  = COLOR + "09"
TEAL      = COLOR + "10"
CYAN      = COLOR + "11"
LT_BLUE   = COLOR + "12"
PINK      = COLOR + "13"
GREY      = COLOR + "14"
LT_GREY   = COLOR + "15"


class Bot(object):

    def __init__(self, settings):
        self.irc = irc.Irc(settings)
        self.settings = settings
        self.bot = self.irc
        self.logger = self.irc.logger
        self.owners = self.settings['owners']
        self.plugins = self.settings['plugins']
        #self._event_loop()
        jobs = [
            gevent.spawn(self.ipc_cli),
            gevent.spawn(self._listen),
        ]
        gevent.joinall(jobs)

    def _reply(self, msg):
        if not self.recipients == self.irc.nick:
            # Reply the message from channel
            self.irc.msg(self.recipients, msg)
        else:
            # Reply to private message
            self.irc.reply(self.user, msg)

    def _say(self, channel, msg):
        if channel.startswith("#"):
            self.irc.msg(channel, msg)
        else:
            self.irc.msg("#" + channel, msg)

    def ipc_cli(self):
        #When start, wait 5 sec until the bot join channels
        gevent.sleep(8)
        #try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(('127.0.0.1', 5050))
        client.send('connected\n')
        print 'connected'
        try:
            while True:
                d = client.recv(1024)
                if not d:
                    #reconnect
                    gevent.sleep(5)
                    try:
                        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client.connect(('127.0.0.1', 5050))
                    except KeyboardInterrupt:
                        print 'Stop'
                        break
                    except socket.error, e:
                        if e.errno == 111:
                            continue
                    except Exception, e:
                        print 'Cannot connect socket, give up: %s' % e
                        break
                    client.send('connected\n')
                # check database, get case and post to IRC
                # 'Done' is sent by server periodically, will receive 'Accepted' is recieved when bot connect to server at the beginning
                elif d == 'Done\n' or d == 'Accepted\n':
                    self.logger.debug("Run job")
                    p = get_collection('cases')
                    new_case_query_str = {
                        '$or': [
                            #{'has_owner': False},
                            {'$and': [
                                {'nno': True},
                                {'mute': False}
                            ]},
                            {'$and': [
                                {'status': 'WoRH'},
                                {'mute': False},
                                {'has_owner': False},
                            ]},
                        ]
                    }
                    now = datetime.now()
		    print now
                    onduty = now.hour in xrange(8, 18) and now.isoweekday() in xrange(1, 6)
                    new_case_output_header = 'Region'.ljust(8)
                    new_case_output_header += ' ' + 'Case Num'.ljust(9)
                    new_case_output_header += ' ' + cjk_string_ljust('Subject', 55)
                    new_case_output_header += ' ' + 'Status'.ljust(7)
                    new_case_output_header += ' ' + cjk_string_ljust('SBT', 6)
                    new_case_output_header += ' ' + 'Sev'.ljust(4)
                    new_case_output_header += ' ' + 'URL'.ljust(42)
                    new_case_output_header += ' ' + 'NNO'.ljust(4)
		     
                    print "Going to print cases"

                    if onduty:
                        self._say('#gss_china', BOLD + '=========New Case===========' + CLEAR)
                        #self._say(self.settings['channels'][0], BOLD + new_case_output_header + CLEAR)
	                self._say('#gss-korea', BOLD + '=========New Case===========' + CLEAR)

                    cases = p.find(new_case_query_str)


		    #   ============= cchen's test ===========
		    sbr_dic = {}


		    #   ===============  end =================
                    for case in cases:
                        if case['region'] == 'HK':
                            msg_prefix = 'HK_Case'
                        elif case['region'] == 'TW':
                            msg_prefix = 'TW_Case'
                        elif case['region'] == 'KR':
                            msg_prefix = 'KR_Case'
                        elif case['region'] == 'CN':
                            msg_prefix = 'CN_Case'
                        else:
                            msg_prefix = 'Global_Case'

                        if case['severity'] == '1':
                            sev_str = BOLD + RED + 'S1' + CLEAR
                        elif case['severity'] == '2':
                            sev_str = BOLD + ORANGE + 'S2' + CLEAR
                        else:
                            sev_str = GREEN + 'S' + case['severity'] + CLEAR

                        if case['sbt'] != '-':
                            if 0 <= int(case['sbt'].replace(',', '')) < 60:
                                sbt_str = BOLD + RED + case['sbt'] + CLEAR
                            elif int(case['sbt'].replace(',', '')) < 0:
                                sbt_str = BOLD + ORANGE + case['sbt'] + CLEAR
                            else:
                                sbt_str = GREEN + case['sbt'] + CLEAR
                        else:
                            sbt_str = case['sbt'].ljust(6)

                        if case['nno'] is True:
                            #msg_str = msg_prefix.ljust(8)
                            #msg_str += ' ' + case['_id'].ljust(9)
                            #msg_str += ' ' + cjk_string_ljust(case['subject'], 60)
                            #msg_str += ' ' + case['status'].ljust(7)
                            #msg_str += ' ' + case['sbt'].ljust(6)
                            #msg_str += ' ' + sev_str.ljust(4)
                            #msg_str += ' ' + case['url'].ljust(40)
                            #msg_str += ' ' + 'True'
                            msg_str = "%s: [%s%s%s] %s%s%s [%s %s] %s%s%s NNO:%s %s" % (
                                msg_prefix,
                                BOLD, case['_id'], CLEAR,
                                BLUE, case['subject'], CLEAR,
                                sbt_str,
                                sev_str,
                                BLUE, case['status'], CLEAR,
                                case['nno'],
                                case['url'],
                            )
                        else:
                            msg_str = "%s: [%s%s%s] %s%s%s [%s %s] %s%s%s %s" % (
                                msg_prefix,
                                BOLD, case['_id'], CLEAR,
                                BLUE, case['subject'], CLEAR,
                                sbt_str,
                                sev_str,
                                BLUE, case['status'], CLEAR,
                                case['url'],
                            )

                        if onduty:
                            self._say(self.settings['channels'][0], msg_str)



			# ============ cchen's test ================

			if onduty and case['region'] == 'KR':

				msg_str = "%s: [%s%s%s] %s%s%s [%s %s] %s%s%s %s" % (
                                msg_prefix,
                                BOLD, case['_id'], CLEAR,
                                BLUE, case['subject'], CLEAR,
                                sbt_str,
                                sev_str,
                                BLUE, case['status'], CLEAR,
                                case['url'],
                            )

				self._say(self.settings['channels'][1],msg_str)
		    if onduty:
		    	print "SBR_MSG in bot.py" + backend.SBR_MSG
		    	q = get_collection('ncq')
		    	SBR_MSG = q.find_one({'_id':200})['content']
		    	self._say(self.settings['channels'][0],SBR_MSG)

                    # get escalation cases
                    gevent.sleep(30)
                    p = get_collection('escalation')
                    escalation_query_str = {'checked': False}
                    escalation_cases = p.find(escalation_query_str)
                    if escalation_cases.count() > 0:
                        self._say(self.settings['channels'][0], BOLD + '=========Escalation Case===========' + CLEAR)
                        for case in escalation_cases:
                            msg = "jaylin: %s %s %s %s" % (
                                case['_id'],
                                case['account'],
                                case['subject'],
                                case['url'],
                            )
                            if onduty:
                                self._say(self.settings['channels'][0], msg)
                else:
                    continue
        except:
            print 'No server running...'
            print sys.exc_info()

    @irc.log
    def _listen(self):

        while True:
            owners = self.settings['owners']
            line = self.irc.lines.get()
            self.msgs = line['args'][-1]
            self.recipients = line['args'][0]
            self.user = line['prefix'].split('!', 1)[0]

            if self.msgs.startswith('^'):
                channel = self.bot.line['args'][0]
                user = self.user
                msg = self.bot.line['args'][-1]
                command = msg.split()[0][1:]
                args = ' '.join(msg.split()[1:])

                try:
                    getattr(commander, command)(self.bot, channel, user, args)
                except Exception, e:
                    self.logger.debug("command: %s" % command)
                    self.logger.debug(str(e))
                    self._reply('command not found')
            elif self.msgs.startswith(self.irc.nick) and re.search('\^[a-zA-Z]+', self.msgs):
                channel = self.bot.line['args'][0]
                user = self.user
                cmd_index = self.bot.line['args'][-1].find('^')
                msg = self.bot.line['args'][-1][cmd_index:]
                command = msg.split()[0][1:]
                args = ' '.join(msg.split()[1:])

                try:
                    getattr(commander, command)(self.bot, channel, user, args)
                except Exception, e:
                    self.logger.debug("command: %s" % command)
                    self.logger.debug(str(e))
                    self._reply('command not found')
            if self.msgs.startswith('#reload') and self.user in owners:
                reload(commander)

    def _event_loop(self):
        '''Main event loop. All the magic happens here.'''

        bot = self.irc
        logger = self.irc.logger
        #line = self.irc.lines.get()
        #msgs = line['args'][-1]
        #self.sender = line['args'][0]
        #self.user = line['prefix'].split('!', 1)[0]
        owners = self.settings['owners']
        plugins = self.settings['plugins']
        while True:
            #bot = self.irc
            #logger = self.irc.logger
            irc.logger.debug("block @ get line")
            line = self.irc.lines.get()
            irc.logger.debug("fly")
            msgs = line['args'][-1]
            self.sender = line['args'][0]
            self.user = line['prefix'].split('!', 1)[0]
            #owners = self.settings['owners']
            #plugins = self.settings['plugins']

            try:
                irc.logger.debug("before spawn jobs")
                jobs = [gevent.spawn(loader.load_plugins, bot, [p]) for p in plugins]
                #jobs.append(gevent.spawn_later(5.0, self._test))
                #gevent.spawn_later(5.0, self._test)
                gevent.joinall(jobs)
                irc.logger.debug("after spawn jobs %s" % jobs)
                if msgs.startswith('^reload') and self.user in owners:
                    self.settings = Config('config.py').config.SETTINGS
                    plugins = self.settings['plugins']
                    plugin = msgs[msgs.find('^reload'):].split(' ', 1)[-1]

                    if not plugin == '^reload' and plugin in plugins:
                        loader.reload_plugin('voxbot.' + plugin)
                        print "sender: %s" % self.sender
                        print "nick: %s" % self.irc.nick
                        self._respond('Reloading {0}'.format(plugin))
                    else:
                        for plugin in plugins:
                            loader.reload_plugin('voxbot.' + plugin)
                        print "sender: %s" % self.sender
                        print "nick: %s" % self.irc.nick
                        self._respond('Reloading plugins')

                if msgs.startswith('^help'):
                    loaded = ' '.join(plugins)
                    plugin = msgs[msgs.find('^help'):].split(' ', 1)[-1]
                    plugin = string.capitalize(plugin)

                    if plugin == '^help':
                        self._respond('Plugins loaded: ' + loaded)
                    elif plugin in plugins:
                        p = [p for p in plugins if p == plugin]
                        p = ''.join(p)
                        info = sys.modules[p].__dict__[p].__doc__
                        self._respond(str(info))
                    else:
                        self._respond('Plugin not found')

            except Exception, e:  # catch all exceptions, don't die for plugins
                logger.error('Error loading plugins: ' + str(e))


class Config(object):
    '''This class returns a config object from a file, `filename`.'''

    def __init__(self, filename):
        self.config = self.from_pyfile(filename)

    def from_pyfile(self, filename):
        filename = os.path.join(os.path.abspath('.'), filename)

        try:
            imp.load_source('config', filename)
            config = sys.modules['config'].__dict__['Config']
            return config
        except ImportError, e:
            print('Config error: ' + e)  # not ideal, should be logger


class Plugin(object):
    '''This is a base class from which plugins may inherit. It provides some
    normalized variables which aim to make writing plugins a sane endevour.
    '''

    # bot = self.irc
    def __init__(self, bot):
        '''
        Msg received when indicate receiver

        :eth2net!~ethinx@106.3.102.85 PRIVMSG #djumpot :djumpot: nothing
        prefix: eth2net!~ethinx@106.3.102.85
        command: PRIVMSG
        args: ['#djumpot', 'djumpot: nothing']

        W/O receiver

        :eth2net!~ethinx@106.3.102.85 PRIVMSG #djumpot :hello world
        prefix: eth2net!~ethinx@106.3.102.85
        command: PRIVMSG
        args: ['#djumpot', 'hello world']

        Only url
        :eth2net!~ethinx@106.3.102.85 PRIVMSG #djumpot :http://google.com/&asdf=123
        prefix: eth2net!~ethinx@106.3.102.85
        command: PRIVMSG
        args: ['#djumpot', 'http://google.com/&asdf=123']
        '''
        self.bot = bot
        self.logger = bot.logger
        self.owners = self.bot.settings['owners']
        self.msgs = self.bot.line['args'][-1]
        # djumpot: nothing
        # hello world
        # http://google.com/&asdf=123
        self.sender = self.bot.line['args'][0]  # #djumpot
        self.command = self.bot.line['command']  # PRIVMSG
        self.prefix = self.bot.line['prefix']  # eth2net!~ethinx@106.3.102.85
        self.user = self.prefix.split('!')[0]  # eth2net
        self.userlist = self.bot.userlist
        self.from_channel = self.bot.line['args'][0]

    def reply(self, msg=None, channel=None, action=None):
        '''Directs a response to either a channel or user. If `channel`,
        overrides the target, if `action`, wraps `msg` with ACTION escapes.
        '''

        LINE_LIMIT = 255

        if not msg:
            msg = 'Error: Received an empty string'
        elif action or (msg.startswith(chr(1)) and action is not False):
            msg = chr(1) + 'ACTION ' + msg + chr(1)

        msgs = [msg[i:i + LINE_LIMIT] for i in range(0, len(msg), LINE_LIMIT)]

        if channel:
            return [self.bot.msg(channel, msg) for msg in msgs]
        if self.sender != self.bot.nick:
            [self.bot.msg(self.sender, msg) for msg in msgs]
        else:
            [self.bot.reply(self.user, msg) for msg in msgs]

    @staticmethod
    def command(cmd, is_in=False):
        '''Used for decorating commands. Should contain the command string.

        Like this:

            @Plugin.command('^my_command')
            def my_command(*args, **kwargs):
                pass # do some cool stuff here

        is_in:
            @Plugin.command('http://', is_in=True)
            def my_command(*args, **kwargs):
                pass # do some cool stuff here

        '''

        def _dec(f):
            from functools import wraps

            @wraps(f)
            def _wrap(self, *args, **kwargs):
                '''
                self.msgs:
                    djumpot: nothing
                    hello world
                    http://google.com/&asdf=123
                '''

                # case 1: djumpot: ^reload MyPlugin
                # case 2: djumpot: hello world ^reload MyPlugin
                # case 3, cmd=http://: djumpot: http://google.com/&asdf=123
                _cmd = self.msgs[self.msgs.find(cmd):].split(' ', 1)[0]
                # case 1: _cmd = ^reload
                # case 2: _cmd = ^reload
                # case 3: _cmd = http://google.com/&asdf=123
                args = self.msgs[self.msgs.find(cmd):].split(' ', 1)[-1]
                # case 1: args = MyPlugin
                # case 2: args = MyPlugin
                # case 3: args = http://google.com/&asdf=123
                if _cmd == args:
                    args = None
                if (is_in and cmd in self.msgs) or self.msgs.startswith(cmd):
                    return f(self, cmd=_cmd, args=args)
            return _wrap
        return _dec

    @staticmethod
    def event(event):
        '''Used for decorating commands that are triggered by an event, such as
        JOIN or PART. Should contain the server command, e.g. JOIN.

        Like this:

            @Plugin.command('JOIN')
            def on_join(*args, **kwargs):
                pass # do some cool stuff here
        '''

        def _dec(f):
            def _wrap(self, *args, **kwargs):
                args = self.msgs
                if event in self.command:
                    return f(self, args)
            return _wrap
        return _dec


# http://python.6.n6.nabble.com/CPyUG-111887-td2746092.html
# string adjust for Chiese chars. I think this should be able to work with CJK chars.
# Change the method name from hz_string_ljust to cjk_string_ljust
def cjk_string_ljust(s, length, fillchar=' '):
    l = string_width(s)
    if fillchar:
        return s.ljust(length - (l - len(s)), fillchar)
    else:
        return s.ljust(length - (l - len(s)))


def cjk_string_rjust(s, length, fillchar=' '):
    l = string_width(s)
    if fillchar:
        return s.rjust(length - (l - len(s)), fillchar)
    else:
        return s.rjust(length - (l - len(s)))


def string_width(text):
    import unicodedata
    s = 0
    for ch in text:
        if isinstance(ch, unicode):
            if unicodedata.east_asian_width(ch) != 'Na':
                s += 2
            else:
                s += 1
        else:
            s += 1
    return s
