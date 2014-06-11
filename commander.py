#!/usr/bin/env python
#coding:utf-8

__author__ = 'eth2net [at] gmail.com'
__email__ = 'eth2net [at] gmail.com'
__date__ = '2013/01/25'

from db import get_collection

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


def help(bot, channel, user, args):
    help_str = 'command format would be "^command <args>", command list: take, mute, unmute, report'
    bot.msg(channel, help_str)


def take(bot, channel, user, cid):
    p = get_collection('cases')
    cid = cid.split()[0]
    try:
        int(cid)
    except:
        bot.msg(channel, '%s: case id incorrect' % user)
        return False
    case = p.find_one({'_id': cid})
    if case is None:
        bot.msg(channel, '%s: case id incorrect' % user)
        return False
    case['owner'] = user
    case['mute'] = False
    case['has_owner'] = True
    if not case['nno']:
        case['nno'] = False
    p.update({'_id': cid}, case)
    bot.msg(channel, 'gss_china: %s take case %s %s' % (user, case['_id'], case['subject']))


def mute(bot, channel, user, cid):
    p = get_collection('cases')
    case = p.find_one({'_id': cid})
    if case:
        case['mute'] = True
        p.update({'_id': cid}, case)
        if channel == bot.nick:
            bot.reply(user, 'mute case: %s' % cid)
        else:
            bot.msg(channel, '%s, mute case: %s' % (user, cid))
    else:
        if channel == bot.nick:
            bot.reply(user, 'I can\'t find the case %s' % cid)
        else:
            bot.msg(channel, '%s, I can\'t find the case: %s' % (user, cid))


def unmute(bot, channel, user, cid):
    p = get_collection('cases')
    case = p.find_one({'_id': cid})
    if case:
        case['mute'] = False
        p.update({'_id': cid}, case)
        if channel == bot.nick:
            bot.reply(user, 'mute case: %s' % cid)
        else:
            bot.msg(channel, '%s, mute case: %s' % (user, cid))
    else:
        if channel == bot.nick:
            bot.reply(user, 'I can\'t find the case %s' % cid)
        else:
            bot.msg(channel, '%s, I can\'t find the case: %s' % (user, cid))


def report(bot, channel, user, args):
    p = get_collection('cases')
    query_str = {
        '$or': [
            {'has_owner': False},
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
    cases = p.find(query_str)
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
            sev_str = case['severity']

        if case['sbt'] != '-':
            if 0 <= int(case['sbt'].replace(',', '')) < 60:
                sbt_str = BOLD + ORANGE + case['sbt'] + CLEAR
            elif int(case['sbt'].replace(',', '')) < 0:
                sbt_str = BOLD + ORANGE + case['sbt'] + CLEAR
            else:
                sbt_str = GREEN + case['sbt'] + CLEAR
        else:
            sbt_str = case['sbt']

        msg_str = "%s: [%s%s%s] [%s] %s%s%s%s [%s %s] %s NNO:%s %s" % (
            msg_prefix,
            BOLD, case['_id'], CLEAR,
            case['account'],
            BOLD, BLUE, case['subject'], CLEAR,
            sbt_str,
            sev_str,
            case['status'],
            case['nno'],
            case['url'],
        )
        bot.msg(channel, user + ' ' + msg_str)


def dhex(bot, channel, user, number):
    try:
        int(number)
    except:
        bot.msg(channel, user + ' you input an incorrect number')
    bot.msg(channel, user + ' ' + hex(int(number)))


def dbin(bot, channel, user, number):
    try:
        int(number)
    except:
        bot.msg(channel, user + ' you input an incorrect number')
    bot.msg(channel, user + ' ' + bin(int(number)))


def hexd(bot, channel, user, number):
    if number.startswith('0x'):
        bot.msg(channel, user + ' ' + str(int(number, 16)))
    else:
        bot.msg(channel, user + ' you input an incorrect number')


def bind(bot, channel, user, number):
    if number.startswith('0b'):
        bot.msg(channel, user + ' ' + str(int(number, 2)))
    else:
        bot.msg(channel, user + ' you input an incorrect number')

if __name__ == '__main__':
    pass
