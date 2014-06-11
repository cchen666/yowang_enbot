import gevent
import logging
import time
import sys

from gevent import socket, queue
from gevent.ssl import wrap_socket

logger = logging.getLogger('irc')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = \
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def log(func):
    def wrap(*args, **kwargs):
        logger.debug("%s %s" % (__file__, func.__name__))
        return func(*args, **kwargs)
    return wrap

class Tcp(object):
    '''Handles TCP connections, `timeout` is in secs.'''

    def __init__(self, host, port, timeout=300):
        self._ibuffer = ''
        self._obuffer = ''
        self.iqueue = queue.Queue()
        self.oqueue = queue.Queue()
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket = self._create_socket()

    def _create_socket(self):
        return socket.socket()

    def connect(self):
        try:
            self._socket.connect((self.host, self.port))
        except:
            logger.error("Failed connect")
            sys.exit()

        jobs = [gevent.spawn(self._recv_loop), gevent.spawn(self._send_loop)]
        try:
            gevent.joinall(jobs)
        finally:
            gevent.killall(jobs)

    def disconnect(self):
        self._socket.close()
        logger.debug("Disconnect...")

    def _recv_loop(self):
        while True:
            data = self._socket.recv(4096)
            self._ibuffer += data
            while '\r\n' in self._ibuffer:
                line, self._ibuffer = self._ibuffer.split('\r\n', 1)
                self.iqueue.put(line)

    def _send_loop(self):
        while True:
            line = self.oqueue.get().splitlines()[0][:500]
            self._obuffer += line.encode('utf-8', 'replace') + '\r\n'
            while self._obuffer:
                sent = self._socket.send(self._obuffer)
                self._obuffer = self._obuffer[sent:]


class SslTcp(Tcp):
    '''SSL wrapper for TCP connections.'''

    def _create_socket(self):
        return wrap_socket(Tcp._create_socket(self), server_side=False)


class IrcNullMessage(Exception):
    pass


class Irc(object):
    '''Provides a basic interface to an IRC server.'''

    def __init__(self, settings):
        self.settings = settings
        self.server = settings['server']
        self.nick = settings['nick']
        self.realname = settings['realname']
        self.port = settings['port']
        self.ssl = settings['ssl']
        self.channels = settings['channels']
        self.userlist = {}
        self.line = {'prefix': '', 'command': '', 'args': ['', '']}
        self.lines = queue.Queue() # responses from the server
        self.logger = logger
        self.connected = False

        self._connect()
        gevent.spawn(self._event_loop)

    def _create_connection(self):
        transport = SslTcp if self.ssl else Tcp
        return transport(self.server, self.port)

    def _connect(self):
        self.conn = self._create_connection()
        gevent.spawn(self.conn.connect)
        self._set_nick(self.nick)
        self.cmd('USER', (self.nick, ' 3 ', '* ', self.realname))

    def _disconnect(self):
        self.conn.disconnect()

    def _parsemsg(self, s):
        '''
        Breaks a message from an IRC server into its prefix, command,
        and arguments.
        '''

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
        '''
        prefix = ''
        trailing = []
        if not s:
            raise IrcNullMessage('Received an empty line from the server.')
        if s[0] == ':':
            prefix, s = s[1:].split(' ', 1)
        if s.find(' :') != -1:
            s, trailing = s.split(' :', 1)
            args = s.split()
            args.append(trailing)
        else:
            args = s.split()
        command = args.pop(0)
        return prefix, command, args

    def _event_loop(self):
        '''
        The main event loop.

        Data from the server is parsed here using `parsemsg`. Parsed events
        are put in the object's event queue, `self.events`.
        '''

        m = 0
        while True:
            line = self.conn.iqueue.get()
            logger.info("Recv : %s" % line)
            prefix, command, args = self._parsemsg(line)
            self.line = {'prefix': prefix, 'command': command, 'args': args}
            self.lines.put(self.line)
            if command == '433': # nick in use
                self.nick = self.nick + '_'
                self._set_nick(self.nick)
            if command == 'PING':
                self.cmd('PONG', args)
            if command == '001':
                self._join_chans(self.channels)
            # Record userlist of channels
            # self.line = ':hubbard.freenode.net 353 djumpot = #ubuntu :djumpot noxd hargut Amzul'
            # self.line['args'] = ['djumpot', '=', '#ubuntu', 'djumpot noxd hargut Amzul']
            if command == '353':
                channel = self.line['args'][2]
                if self.userlist.has_key(channel):
                    self.userlist[channel] += self.line['args'][3:][0].split()
                else:
                    self.userlist[channel] = self.line['args'][3:][0].split()
            # Update userlist
            if command == 'JOIN':
                channel = self.line['args'][0]
                user = self.line['prefix'].split('!')[0]
                if self.userlist.has_key(channel):
                    self.userlist[channel].append(user)
            if command == 'PART' or command == 'QUIT':
                channel = self.line['args'][0]
                user = self.line['prefix'].split('!')[0]
                print 'user---:', user
                print self.userlist
                if self.userlist.has_key(channel):
                    if '@'+user in self.userlist[channel]:
                        self.userlist[channel].remove('@'+user)
                    else:
                        self.userlist[channel].remove(user)
            if command == 366:
                m += 1
                if m == len(self.channels):
                    self.connected = True

    def _set_nick(self, nick):
        self.cmd('NICK', nick)

    def _join_chans(self, channels):
        return [self.cmd('JOIN', channel) for channel in channels]

    def ctcp_reply(self, target, msg):
        msg = chr(1) + msg + chr(1)
        self.notice(target, msg)

    def ctcp_send(self, target, msg):
        msg = chr(1) + msg + chr(1)
        self.msg(target, msg)

    def does(self, target, msg):
        msg = chr(1) + 'ACTION ' + msg + chr(1)
        self.msg(target, msg)

    def reply(self, prefix, msg):
        self.msg(prefix.split('!')[0], msg)

    def msg(self, target, msg):
        self.cmd('PRIVMSG', (target + ' :' + msg))

    def notice(self, target, msg):
        self.cmd('NOTICE', (target + ' :' + msg))

    def cmd(self, command, args, prefix=None):

        if prefix:
            self._send(prefix + command + ' ' + ''.join(args))
        else:
            self._send(command + ' ' + ''.join(args))

    def _send(self, s):
        logger.info("Sent : %s" % s)
        self.conn.oqueue.put(s)


if __name__ == '__main__':

    SETTINGS = {
        #'server': 'irc.voxinfinitus.net',
        'server': 'irc.freenode.net',
        #'nick': 'Kaa',
        'nick': 'ksir',
        'realname': 'ksir',
        'port': 6667,
        'ssl': False,
        #'channels': ['#voxinfinitus', '#radioreddit', '#techsupport'],
        'channels': ['#ksir'],
        }

    bot = lambda : Irc(SETTINGS)
    jobs = [gevent.spawn(bot)]
    gevent.joinall(jobs)

