#!/usr/bin/env python
# coding=utf-8

import urllib2, urllib
#import urlparse
from bs4 import BeautifulSoup
from bs4 import Tag
import os
import pprint

local_dir = './image'
host = 'http://news.family.baidu.com/topicComments'
header = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',
		'Connection' : 'keep-alive',
		'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		'Accept-Language' : 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0'
}

def getPage(pageNum, pageSize=9):
# if move req outside this function will encounter some exception: see main and processTotal
    data = {
        'page': pageNum,
        'articleId': 161988,
        'pageSize': pageSize
    }
    dataStr = urllib.urlencode(data)
    #print dataStr
    url = '%s/commentlistpage' % host
    req = urllib2.Request(url, dataStr, headers=header)
    res = urllib2.urlopen(req)
    return res.read()

def download(url, timeout=30):
    dheader = header.copy()
    dheader['Accept'] = 'image/webp,image/*,*/*;q=0.8'
    #dheader['Host'] = urlparse.urlparse(url).netloc
    dheader['Referer'] = host
    #print dheader
    req = urllib2.Request(url, headers=dheader)
    res = urllib2.urlopen(req, timeout=timeout)
    content = res.read()
    if not os.path.isdir(local_dir):
        os.mkdir(local_dir)
    filename = '%s/%s' % (local_dir, os.path.basename(url))
    suffix = 0
    basename, ext = os.path.splitext(filename)
    while os.path.exists(filename):
        filename = '%s-%d%s' % (basename, suffix, ext)
        suffix += 1
    with open(filename, 'w') as f:
        f.write(content)
    res.close()
    return filename

def getTotalNum():
    content = getPage(1, 1)
    soup = BeautifulSoup(content, 'lxml')
    tag_input = soup.find('input', attrs={'name':'commentCount'})
    return int(tag_input['value'])

def getFloor(floor):
    tnum = getTotalNum()
    content = getPage(tnum + 1 - floor, 1)
    return content

def to_string(tag):
    res = []
    for c in tag.children:
        if isinstance(c, Tag) and c.name == u'br':
            res.append(u'\n')
        else:
            res.append(unicode(c))
    return ''.join(res)

def multi_download(url):
    pass

def processPage(content):
    soup = BeautifulSoup(content, 'lxml')
    div_list = soup.find('div', class_='list')
    result = []
    for item in div_list.find_all('div', class_='item'):
        res = {}
        res['floor'] = unicode(item.find('span', class_='floor').string)
        print res['floor']
        info = item.find('span', class_='name')
        if info.has_attr('title'):
            res['dept'] = info['title']
        res['uname'] = unicode(info.string)
        res['hi_link'] = unicode(item.find('a', class_='hi'))
        comment_div = item.find('div', class_='content')
        res['comment'] = comment_div.children.next().strip()
        t = lambda url: (url, download(url))
        res['imgs'] = [t(img_div.img['src']) for img_div in comment_div.find('div', class_='imgList').find_all('div', class_='imgItem')]
        count_p = item.find('p', class_='replySupport')
        res['support_count'] = int(count_p.find('span', class_='supportComment').em.string)
        res['reply_count'] = int(count_p.find('span', class_='readComments').em.string)
        reply_divs = item.find('div', class_='replys').find('div', class_='replyList').find_all('div', class_='rItem')
        res['replys'] = [to_string(rdiv.find('span', class_='replyAuthor'))
                + to_string(rdiv.find('div', class_='rContent'))
                for rdiv in reply_divs]
        result.append(res)
    return result


def processNPage(n=9):
    tnum = getTotalNum()
    pageCount = (tnum + n - 1) / n
# 如果getPage 中的req 移到函数外时
# 循环抓取10 及其以上后，返回不是预期的页面
    res = []
    for i in xrange(pageCount):
        content = getPage(i+1)
        res.extend(processPage(content))
    return res

def processTotal():
    tnum = getTotalNum()
# 如果getPage 中的req 移到函数外时
# getTotalNum 抓一次后，getPage 抓第二次返回不是预期
    content = getPage(1, tnum)
    return processPage(content)


if __name__ == '__main__':
    #processNPage()
    #print processPage(getFloor(907))
    with open('out', 'w') as f:
        pprint.pprint(processTotal(), f)
