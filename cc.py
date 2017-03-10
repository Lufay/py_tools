#!/usr/bin/env python
# coding=utf-8

import urllib2, urllib
from bs4 import BeautifulSoup

url = 'http://news.family.baidu.com/topicComments/commentlistpage'
header = { 'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36',
		'Connection' : 'keep-alive',
		'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
		'Accept-Language' : 'zh-CN,zh;q=0.8',
        'Cache-Control': 'max-age=0'
}

def getPage(pageNum, pageSize=9):
# if move req outside this function will encounter some exception: see main and processTotal
    req = urllib2.Request(url, headers=header)
    data = {
        'page': pageNum,
        'articleId': 161988,
        'pageSize': pageSize
    }
    dataStr = urllib.urlencode(data)
    print dataStr
    res = urllib2.urlopen(req, dataStr)
    return res.read()

def getTotalNum():
    content = getPage(1, 1)
    soup = BeautifulSoup(content, 'lxml')
    tag_input = soup.find('input', attrs={'name':'commentCount'})
    return int(tag_input['value'])

def getFloor(floor):
    tnum = getTotalNum()
    content = getPage(tnum + 1 - floor, 1)
    return content

def processPage(content):
    soup = BeautifulSoup(content, 'lxml')
    div_list = soup.find('div', class_='list')
    result = []
    for item in div_list.find_all('div', class_='item'):
        res = {}
        res['floor'] = item.find('span', class_='floor').string
        print res
        info = item.find('span', class_='name')
        res['dept'] = info['title']
        res['uname'] = info.string
        res['hi_link'] = item.find('a', class_='hi').encode()
        comment_div = item.find('div', class_='content')
        res['comment'] = comment_div.children.next().strip()
        res['imgs'] = [img_div.img['src'] for img_div in comment_div.find('div', class_='imgList').find_all('div', class_='imgItem')]
        count_p = item.find('p', class_='replySupport')
        res['support_count'] = int(count_p.find('span', class_='supportComment').em.string)
        res['reply_count'] = int(count_p.find('span', class_='readComments').em.string)
        reply_divs = item.find('div', class_='replys').find('div', class_='replyList').find_all('div', class_='rItem')
        print reply_divs
        res['replys'] = [rdiv.find('span', class_='replyAuthor').string
                + rdiv.find('div', class_='rContent').string
                for rdiv in reply_divs]
        result.append(res)
    return result


def processNPage(n=9):
    tnum = getTotalNum()
    pageCount = (tnum + n - 1) / n
# 循环抓取10 及其以上后，返回不是预期的页面
    for i in xrange(pageCount):
        content = getPage(i+1)
        processPage(content)

def processTotal():
    tnum = getTotalNum()
# getTotalNum 抓一次后，getPage 抓第二次返回不是预期
    content = getPage(1, tnum)
    processPage(content)


if __name__ == '__main__':
    #processNPage()
    #processTotal()

    processPage(getFloor(963))

