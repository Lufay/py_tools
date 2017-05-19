#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import urllib2, urllib, cookielib, httplib
import time, datetime
import re
from lxml import etree
import json
import pprint
#from PIL import Image
import subprocess
import random
import functools

host='https://wx.qq.com'
host2='https://login.wx.qq.com'
header = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',
		'Connection' : 'keep-alive',
		'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/*,*/*;q=0.8',
		'Accept-Language' : 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0'
}
header_json = header.copy()
header_json.update({
    'Accept': 'application/json,text/plain,*/*',
    'Content-Type': 'application/json;charset=UTF-8'
})
device_id = 'e' + str(random.random())[2:17]
contact_dict = {
    'newsapp': {
        'NickName': u'腾讯新闻',
        'RemarkName': u'',
        'Signature': u'',
        'Sex': 0,
        'Members': {},
        'EncryChatRoomId': u''
    }
}
sex_map = {0: u'未知', 1: u'男', 2: u'女'}

def installCookieOpener():
    cookie = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    urllib2.install_opener(opener)

def request(url, data=None, headers=None, retry=5):
    req = urllib2.Request(url, data, headers=header if headers is None else headers)
    for _ in xrange(retry):
        try:
            res = urllib2.urlopen(req)
            return res.read()
        except urllib2.HTTPError, e:
            print "Caght a HTTP except!\n%s" % e.reason
        except urllib2.URLError, e:
            print "Caght a URL except!\n%s" % e
        except httplib.BadStatusLine, e:
            print "Caght a BadStatusLine except!\n%s" % e
        except Exception, e:
            print "Caght a unknown except!\n%s" % e.message
        time.sleep(_ + 1)
    else:
        print "Retry failed!"

def getUUID():
    red_uri = '%s/cgi-bin/mmwebwx-bin/webwxnewloginpage' % host
    arg = {
        'appid': 'wx782c26e4c19acffb',
        'redirect_uri': red_uri,
        'fun': 'new',
        'lang': 'zh_CN',
        '_': int(time.time() * 1000)
    }
    url = '%s/jslogin?%s' % (host2, urllib.urlencode(arg))
    print url
    res = request(url)
    print res
    pattern = re.compile(r'window.QRLogin.code = 200; window.QRLogin.uuid = "([\w-]+==)";')
    mat = pattern.match(res)
    if mat:
        return mat.group(1)

def showQrCode(uuid):
    url = 'https://login.weixin.qq.com/qrcode/%s' % uuid
    with open('qrcode', 'w') as f:
        f.write(request(url))
    #im = Image.open('a')
    #im.show()
    subprocess.check_call('imgcat qrcode', shell=True)

def bitNot(num, width=32):
    t = 2 ** width
    return t + ~(num % t)

def loginDetect(uuid, uuid_time=None, retry=10):
    detect_uri = '%s/cgi-bin/mmwebwx-bin/login' % host2
    now = int(time.time() * 1000)
    arg = {
        'loginicon': 'true',
        'uuid': uuid,
        'tip': 0,
        'r': bitNot(now),
        '_': now if uuid_time is None else uuid_time
    }
    pattern = re.compile(r'''window.code=200;
window.redirect_uri="((https://wx\d*.qq.com)/cgi-bin/mmwebwx-bin/webwxnewloginpage.*)";''')
    for _ in xrange(retry):
        arg['_'] += 1
        arg['r'] = bitNot(int(time.time() * 1000))
        url = '%s?%s' % (detect_uri, urllib.urlencode(arg))
        res = request(url)
        print `res`
        mat = pattern.match(res)
        if mat:
            return mat.group(1), mat.group(2)

def parseXML(xml):
    doc = {}
    root = etree.XML(xml)
    for tag in root:
        doc[tag.tag] = tag.text
    return doc

def genTokenPack(func):
    def call_func(wxuin, wxsid, skey, pass_ticket=None, *args, **kwargs):
        data = {
            'BaseRequest': {
                'Uin': wxuin,   # weixin user identity number
                'Sid': wxsid,   # weixin session id
                'Skey': skey,   # one-time password
                'DeviceID': device_id
            }
        }
        if pass_ticket is None:
            return func(data, *args, **kwargs)
        else:
            return func(data, pass_ticket, *args, **kwargs)
    return call_func

@genTokenPack
def getInfo(token_pack, pass_ticket):
    uri = '%s/cgi-bin/mmwebwx-bin/webwxinit' % host
    arg = {
        'r': bitNot(int(time.time() * 1000)),
        'lang': 'zh_CN',
        'pass_ticket': pass_ticket
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    res = request(url, json.dumps(token_pack), header_json)
    #print `res`
    info = json.loads(res)
    if info['BaseResponse']['Ret'] != 0:
        print info['BaseResponse']['ErrMsg']
    else:
        return info['User'], info['SyncKey'], info['ChatSet']

@genTokenPack
def statusNotify(token_pack, pass_ticket, my_name):
    '''
    通知手机端更新状态
    '''
    uri = '%s/cgi-bin/mmwebwx-bin/webwxstatusnotify' % host
    arg = {
        'lang': 'zh_CN',
        'pass_ticket': pass_ticket
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    token_pack.update({
        'ClientMsgId': int(time.time() * 1000),
        'Code': 3,
        'FromUserName': my_name,
        'ToUserName': my_name
    })
    ret = request(url, json.dumps(token_pack), header_json)
    res = json.loads(ret)
    if res['BaseResponse']['Ret'] != 0:
        print res['BaseResponse']['ErrMsg']
    else:
        return res['MsgID']

def getContact(pass_ticket, skey):
    '''
    needs cookie
    '''
    uri = '%s/cgi-bin/mmwebwx-bin/webwxgetcontact' % host
    arg = {
        'r': int(time.time() * 1000),
        'seq': 0,
        'skey': skey,
        'pass_ticket': pass_ticket
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    ret = request(url, headers=header_json)
    res = json.loads(ret)
    if res['BaseResponse']['Ret'] != 0:
        print res['BaseResponse']['ErrMsg']
    else:
        return res['MemberList']

@genTokenPack
def getContactByUserName(token_pack, users_name):
    if len(users_name) == 0:
        return []
    uri = '%s/cgi-bin/mmwebwx-bin/webwxbatchgetcontact' % host
    arg = {
        'type': 'ex',
        'r': int(time.time() * 1000),
        'lang': 'zh_CN'
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    token_pack['Count'] = len(users_name)
    token_pack['List'] = []
    for user_name in users_name:
        if len(user_name) > 0:
            token_pack['List'].append({
                'UserName': user_name,
                'EncryChatRoomId': ""
            })
    ret = request(url, json.dumps(token_pack), header_json)
    res = json.loads(ret)
    if res['BaseResponse']['Ret'] != 0:
        print res['BaseResponse']['ErrMsg']
    else:
        return res['ContactList']

def storeContactDict(contacts):
    for c in contacts:
        mem_dict = {}
        if 'MemberCount' in c and c['MemberCount'] > 0:
            for m in c['MemberList']:
                mem_dict[m['UserName']] = {
                    'NickName': m['NickName'],
                    'DisplayName': m['DisplayName'],
                }
        contact_dict[c['UserName']] = {
            'NickName': c['NickName'],
            'RemarkName': c['RemarkName'],
            'Signature': c['Signature'],
            'Sex': sex_map[c['Sex']],
            'Members': mem_dict,
            'EncryChatRoomId': c['EncryChatRoomId'] if 'EncryChatRoomId' in c else "0"
        }

def formatSyncKey(sync_key_dict):
    '''
    sync_key_dict format is like:
    {u'Count': 4, u'List': [{u'Val': 654568544, u'Key': 1}, {u'Val': 654568630, u'Key': 2}, {u'Val': 654568601, u'Key': 3}, {u'Val': 1494307801, u'Key': 1000}]}
    '''
    sync_keys = ['%d_%d' % (item['Key'], item['Val']) for item in sync_key_dict['List']]
    return '|'.join(sync_keys)

def syncCheck(wxuin, wxsid, skey, sync_key):
    uri = '%s/cgi-bin/mmwebwx-bin/synccheck' % host.replace('wx', 'webpush.wx', 1)
    arg = {
        'r': int(time.time() * 1000),
        'skey': skey,
        'sid': wxsid,
        'uin': wxuin,
        'deviceid': device_id,
        'synckey': formatSyncKey(sync_key),
        '_': int(time.time() * 1000)
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    ret = request(url)
    print `ret`
    pattern = re.compile(r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}')
    mat = pattern.match(ret)
    if mat:
        retcode = int(mat.group(1))
        if retcode == 0:
            return int(mat.group(2))
        elif retcode == 1101:
            sys.exit(0)
        else:
            print 'Unknown retcode %d' % retcode
            sys.exit(1)
    else:
        print 'No match the pattern!'
        sys.exit(1)

@genTokenPack
def syncMsg(token_pack, sync_key):
    '''
    return AddMsgList and SyncKey
    '''
    uri = '%s/cgi-bin/mmwebwx-bin/webwxsync' % host
    arg = {
        'sid': token_pack['BaseRequest']['Sid'],
        'skey': token_pack['BaseRequest']['Skey']
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    token_pack['SyncKey'] = sync_key
    token_pack['rr'] = bitNot(int(time.time() * 1000))
    ret = request(url, json.dumps(token_pack), header_json)
    #print ret
    res = json.loads(ret)
    if res['BaseResponse']['Ret'] != 0:
        print res['BaseResponse']['ErrMsg']
    else:
        return res['AddMsgList'], res['SyncKey'], res['ModContactList'], res['DelContactList']


def showMsg(msg_list, process_pre_msg=None, process_post_msg=None):
    for msg in msg_list:
        if hasattr(process_pre_msg, '__call__'):
            process_pre_msg(msg)
        recv_time = datetime.datetime.fromtimestamp(msg['CreateTime'])
        from_user = contact_dict[msg['FromUserName']]
        to_user = contact_dict[msg['ToUserName']]
        real_content = content = msg['Content'].replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        if msg['FromUserName'].startswith('@@') and content.startswith('@'):
            index = content.find(':')
            if index >= 0:
                from_group_username = content[:index]
                from_group_user = from_user['Members'][from_group_username]
                real_content = content[index+1:]
                content = content.replace(from_group_username, from_group_user['NickName'] if len(from_group_user['DisplayName']) == 0 else from_group_user['DisplayName'], 1)
        msg['Content'] = real_content
        print u'''%s
%s 发给 %s :
%s
''' % (recv_time,
        from_user['NickName'] if len(from_user['RemarkName']) == 0 else from_user['RemarkName'],
        to_user['NickName'] if len(to_user['RemarkName']) == 0 else to_user['RemarkName'],
        content)
        if hasattr(process_post_msg, '__call__'):
            process_post_msg(msg)

def showMsgImg(skey, msg_id, img_type):
    uri = '%s/cgi-bin/mmwebwx-bin/webwxgetmsgimg' % host
    arg = {
        'MsgID': msg_id,
        'skey': skey,
        'type': img_type
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    with open('%s.png' % msg_id, 'w') as f:
        f.write(request(url))
    subprocess.check_call('imgcat %s.png' % msg_id, shell=True)


def main():
    installCookieOpener()
    uuid = getUUID()
    if uuid is None:
        sys.exit(1)
    showQrCode(uuid)
    red_uri, host = loginDetect(uuid)   # modify host
    url = '%s&fun=new&version=v2' % red_uri
    ret = parseXML(request(url))    # set-cookies
    user, sync_key, chatSet = getInfo(ret['wxuin'], ret['wxsid'], ret['skey'], ret['pass_ticket'])
    statusNotify(ret['wxuin'], ret['wxsid'], ret['skey'], ret['pass_ticket'], user['UserName'])
    contacts = getContact(ret['pass_ticket'], ret['skey'])
    if contacts is None:
        sys.exit(2)
    contacts.append(user)
    storeContactDict(contacts)

    getContactByUserNames = functools.partial(getContactByUserName, ret['wxuin'], ret['wxsid'], ret['skey'], None)
    def addGroup(users_name):
        group = getContactByUserNames([g for g in users_name.split(',') if g.startswith('@@')])
        if group is None:
            sys.exit(3)
        storeContactDict(group)

    addGroup(chatSet)
    def do_post_msg(msg):
        try:
            root = etree.XML(msg['Content'])
            for tag in root:
                if tag.tag == 'emoji':
                    showMsgImg(ret['skey'], msg['MsgId'], 'big')
        except etree.XMLSyntaxError, e:
            pass

    while True:
        s = syncCheck(ret['wxuin'], ret['wxsid'], ret['skey'], sync_key)
        if s == 2 or s == 1 or s == 4:
            for retry in xrange(5):
                sync_res = syncMsg(ret['wxuin'], ret['wxsid'], ret['skey'], sync_key=sync_key)
                if sync_res is None:
                    print 'retry sync msg %d' % retry
                else:
                    break
            else:
                print 'retry sync msg failed!'
                sys.exit(5)
            add_msg_list, sync_key, mod_contacts, del_contacts = sync_res
            showMsg(add_msg_list, lambda msg: addGroup(msg['StatusNotifyUserName']), do_post_msg)
            storeContactDict(mod_contacts)
        elif s != 0:
            break

if __name__ == '__main__':
    main()
