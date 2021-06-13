#!/usr/bin/env python3
# coding: utf-8

import sys
import os
import re

from time import sleep, strftime, localtime
from threading import Thread
from functools import reduce

from requests.packages import urllib3
import requests
from lxml import etree
from urllib.parse import urlsplit, urljoin

proxies = {
    "http": "socks5://127.0.0.1:8081",
    "https": "socks5://127.0.0.1:8081"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36",
    "Cookie": "username=admin;",
}

post_data = {
    "username": "admin",
    "password": "123456",
    "code": 0000,
}

# Content-Type白名单
white_type = [
    "text/html",
    # "application/javascript",
]
# 后缀黑名单
black_ext = [
    "jpg", "png", "gif", "css",
    "docx", "xlsx", "pptx", "doc", "xls", "ppt",
]
# Title关键字筛选
title_keys = [
    "系统", "后台", "平台", "管理", "登录", "登陆", "入口",
    "admin", "login",
]
# Title黑名单屏蔽
black_title = [
    "公告", "通知", "公示", "政策", "指示", "办法",
    "会议", "解读", "事项", "官方", "官网",
]

# 域名黑名单
black_domain = [
    "beian.gov.cn", "miit.gov.cn", "www.gov.cn",
    "baidu.com", "weibo.com", "qq.com",
    "people.com.cn", "apple.com",
]

# HTML报告模板头
html_head = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>%s</title>
    <link rel="stylesheet" href="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/css/bootstrap.min.css">
    <script src="https://cdn.staticfile.org/jquery/2.1.1/jquery.min.js"></script>
    <script src="https://cdn.staticfile.org/twitter-bootstrap/3.3.7/js/bootstrap.min.js"></script>
    <script>function del(){$("#"+$("#title").val()).remove()};</script>
</head>
<body>
    <table class="table table-hover" style="word-break: break-all; word-wrap: break-all;">
        <caption>
            <b>%s</b>&emsp;%s&emsp;
            <input type="text" id="title" placeholder="批量删除Title" />
            <input type="submit" name="确认" onclick="del()" />
            <div class="pull-right">Powered by hosch3n@ZhuriLab&emsp;</div>
        </caption>
        <thead>
            <tr><th>Title</th><th>URL</th></tr>
        </thead>
        <tbody>
"""

# 初始目标
target = ""
# 项目名称
project = ""
# 任务队列
task_set = set()
# 去重队列
his_set = set()
# 结果字典
title_url = {}
# IP正则
ipr = re.compile(r"^((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$")
# 线程列表
threads = []

# 关闭SSL报错
urllib3.disable_warnings()

# 发起请求，通过session方法tcp复用
req = requests.session()
def do_req(url, headers=""):
    try:
        pre_res = req.head(url, timeout=(9), allow_redirects=True, verify=False)
        restype = pre_res.headers["Content-Type"].split(";")[0]
        if restype not in white_type:
            return None
        result = req.get(url=url, headers=headers, timeout=(9, 18), verify=False)
        if result.status_code == 200 or result.status_code == 401:
            return result
    except requests.exceptions.RequestException as e:
        print(f"\033[91m[ReqError]: \033[0m{e}\n=>{url}")
        return None
    except KeyError as e:
        print(f"\033[93m[TypeError]: \033[0m{e}\n=>{url}")
        return None

# 对req请求获取的结果编码
def result_decode(result):
    try:
        html = result.content.decode(result.apparent_encoding)
    except UnicodeDecodeError as e:
        print(f"\033[91m[UnicodeDecodeError]: \033[0m{e}")
        html = None
    except TypeError as e:
        print(f"\033[91m[DecodeTypeError]: \033[0m{e}")
        html = None
    finally:
        return html

# 初始化html报告
def init_html():
    ctime = strftime("%Y-%m-%d %H:%M:%S", localtime())
    with open(f"./origin_report/{project}.html", "w+") as fileo:
        fileo.write(html_head % ("提取结果", project, ctime))
    with open(f"./filter_report/{project}.html", "w+") as fileo:
        fileo.write(html_head % ("筛选结果", project, ctime))

# 生成html报告
def gen_html(title, url):
    html = f"""<tr id="{title[0].strip()}"><td>{title}</td><td><a href="{url}" target="_blank">{url}</a></td></tr>"""
    with open(f"./origin_report/{project}.html", "a") as fileo:
        fileo.write(html)
    # 剔除黑名单title
    def judge_black_title():
        for black in black_title:
            if black in str(title):
                return True
    for key in title_keys:
        if key in str(title):
            if judge_black_title():
                break
            with open(f"./filter_report/{project}.html", "a") as fileo:
                fileo.write(html)
            break

# 获取html页面title
def get_title(html, url):
    try:
        selector = etree.HTML(html)
        title = selector.xpath("/html/head/title/text()")
        # print(title, url)
        if url in title_url:
            return None
        title_url[url] = title
        gen_html(title, url)
    except:
        print(f"\033[91m[GetTitleError]: \033[0m{url}")

# 获取html中相关URL
def get_urls(html):
    urls = []
    selector = etree.HTML(html)
    # html中a标签的href
    urls.extend(selector.xpath("//a/@href"))
    # html中option标签的value
    urls.extend(selector.xpath("//option/@value"))
    return urls

def isinternal(ip):
    int_ip = reduce(lambda x,y:(x<<8)+y, map(int, ip.split('.')))
    # ip2int(IP) >> 24
    # [10.255.255.255, 10]; [172.31.255.255, 2753]; [192.168.255.255, 49320]
    return int_ip >> 24 == 10 or int_ip >>20 == 2753 or int_ip >> 16 == 49320 or int_ip >> 24 == 127

# 排除黑名单域名及内网IP，内网域名不做考虑
def judge_urls_task(urls, pscheme, pnetloc, ppath):
    for url in urls:
        parsed_url = urlsplit(url)
        netloc = parsed_url.netloc
        scheme = parsed_url.scheme
        path = parsed_url.path
        query = parsed_url.query
        isip = False
        # 剔除黑名单域名
        def judge_black_domain():
            for dm in black_domain:
                if netloc != '' and netloc.strip().endswith(dm):
                    return True
                else:
                    continue
        # 命中域名黑名单
        if judge_black_domain():
            continue
        # 剔除黑名单后缀
        def judge_black_ext():
            for ext in black_ext:
                if url.strip().endswith(f".{ext}"):
                    return True
                else:
                    continue
        if judge_black_ext():
            continue
        # 剔除JS事件
        if scheme == "javascript":
            continue
        # 剔除内网IP
        if ipr.match(netloc) and isinternal(netloc):
            continue
        # 拼接相对路径
        if scheme == "":
            if "http:" in url or "https:" in url:
                pass
            elif netloc == "":
                url = urljoin(f"{pscheme}{pnetloc}{ppath}", f"{path}?{query}")
            else:
                url = urljoin(f"{pscheme}{netloc}", f"{path}?{query}")
        # 历史记录去重
        if url in his_set:
            continue
        # 是否跳出目标
        if netloc.strip().endswith(target):
            task_set.add(url)
        else:
            result = do_req(url, headers=headers)
            his_set.add(url)
            if result == None:
                continue
            html = result_decode(result)
            if html == None:
                continue
            get_title(html, url)

def run():
    # 重试次数
    retries = 3
    while retries:
        try:
            url = task_set.pop()
            parsed_url = urlsplit(url)
            pscheme = f"{parsed_url.scheme}://"
            pnetloc = parsed_url.netloc.strip()
            ppath = parsed_url.path.strip()
            result = do_req(url, headers=headers)
            his_set.add(url)
            if result == None:
                continue
            html = result_decode(result)
            if html == None:
                continue
            get_title(html, url)
            urls = get_urls(html)
            judge_urls_task(urls, pscheme, pnetloc, ppath)
            retries = 3
        # 任务队列空了
        except KeyError as e:
            print(f"\033[93m[EmptyTask]: \033[0m{e}, wait 3s.")
            retries -= 1
            sleep(3)

def main(argv):
    global target, project
    target = argv[1]
    project = argv[2]
    http_url = f"http://{target}/"
    https_url = f"https://{target}/"

    if not os.path.exists(f"./origin_report/{project}.html"):
        init_html()
    task_set.add(http_url)
    task_set.add(https_url)

    for _ in range(10):
        t = Thread(target=run)
        threads.append(t)
    for t in threads:
        t.start()

if __name__ == "__main__":
    main(sys.argv)