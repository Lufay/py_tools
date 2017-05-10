#!/usr/bin/env python

import sys
import urllib2, urllib, cookielib
import time
import re
from lxml import etree
import json
#from PIL import Image
import subprocess

host='https://wx.qq.com'
host2='https://login.wx.qq.com'
header = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',
		'Connection' : 'keep-alive',
		'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		'Accept-Language' : 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0'
}
header_json = header.copy()
header_json.update({
    'Accept': 'application/json,text/plain,*/*',
    'Content-Type': 'application/json;charset=UTF-8'
})
device_id = 'e950762158418137'
rr_total_timestamp = 1494648619171

def installCookieOpener():
    cookie = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
    urllib2.install_opener(opener)

def request(url, data=None, headers=None):
    req = urllib2.Request(url, data, headers=header if headers is None else headers)
    res = urllib2.urlopen(req)
    return res.read()

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

def loginDetect(uuid, uuid_time=None):
    detect_uri = '%s/cgi-bin/mmwebwx-bin/login' % host2
    arg = {
        'loginicon': 'true',
        'uuid': uuid,
        'tip': 0,
        'r': 1010561045,
        '_': int(time.time() * 1000) if uuid_time is None else uuid_time
    }
    pattern = re.compile(r'''window.code=200;
window.redirect_uri="((https://wx\d*.qq.com)/cgi-bin/mmwebwx-bin/webwxnewloginpage.*)";''')
    for _ in xrange(10):
        arg['_'] += 1
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
                'Uin': wxuin,
                'Sid': wxsid,
                'Skey': skey,
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
        'r': 991828414,
        'lang': 'zh_CN',
        'pass_ticket': pass_ticket
    }
    url = '%s?%s' % (uri, urllib.urlencode(arg))
    res = request(url, json.dumps(token_pack), header_json)
    print `res`
    info = json.loads(res)
    if info['BaseResponse']['Ret'] != 0:
        print info['BaseResponse']['ErrMsg']
    else:
        return info['User'], info['SyncKey']

@genTokenPack
def statusNotify(token_pack, pass_ticket, my_name):
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
    res = request(url, headers=header_json)
    print res

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
    token_pack['rr'] = rr_total_timestamp - int(time.time() * 1000)
    ret = request(url, json.dumps(token_pack), header_json)
    #print ret
    res = json.loads(ret)
    if res['BaseResponse']['Ret'] != 0:
        print res['BaseResponse']['ErrMsg']
    else:
        return res['AddMsgList'], res['SyncKey']

if __name__ == '__main__':
    installCookieOpener()
    uuid = getUUID()
    if uuid == None:
        sys.exit(1)
    showQrCode(uuid)
    red_uri, host = loginDetect(uuid)   # modify host
    url = '%s&fun=new&version=v2' % red_uri
    ret = parseXML(request(url))
    user, sync_key = getInfo(ret['wxuin'], ret['wxsid'], ret['skey'], ret['pass_ticket'])
    #statusNotify(ret['wxuin'], ret['wxsid'], ret['skey'], ret['pass_ticket'], user['UserName'])
    #getContact(ret['pass_ticket'], ret['skey'])
    while True:
        s = syncCheck(ret['wxuin'], ret['wxsid'], ret['skey'], sync_key)
        if s == 2:
            add_msg_list, sync_key = syncMsg(ret['wxuin'], ret['wxsid'], ret['skey'], sync_key=sync_key)
            print add_msg_list
