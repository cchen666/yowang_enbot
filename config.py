class Config(object):

    SETTINGS = {
        'server': 'irc.devel.redhat.com',
        #'nick': 'ksir_beta',
        'nick': 'enbot',
        'realname': 'ksir_beta',
        'port': 6667,
        'ssl': False,
        'channels': [
            #'#ksir',
            '#gss_china',
	    '#gss-korea'	
        ],
        'plugins': [
            'MyPlugin',
        ],
        'owners': ['yowang'],
        'BOTDB': 'enbot',
        'report': {
#            'new_case': 'https://na7.salesforce.com/00OA00000056cak',
            'new_case': 'https://na7.salesforce.com/00OA0000005A735',
            'escalation': 'https://na7.salesforce.com/00OA0000003EkWN',
	    'ncq':'https://na7.salesforce.com/00OA0000005A7oq',
#	    'ncq':'https://na7.salesforce.com/00OA0000005A5es',
        },
        'chk_interval': 900,
    }
