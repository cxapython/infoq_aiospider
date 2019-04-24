# -*- coding: utf-8 -*-
# @Time : 2019-01-28 14:47
# @Author : cxa
# @File : headers_format.py
# @Software: PyCharm
headers = """
Accept: application/json, text/plain, */*
Accept-Encoding: gzip, deflate, br
Accept-Language: zh-CN,zh;q=0.9
Content-Type: application/json
Host: www.infoq.cn
Origin: https://www.infoq.cn
Referer: https://www.infoq.cn/article/Ns2yelhHTd0rhmu2-IzN
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36
"""
hs = headers.split('\n')
b = [k for k in hs if len(k)]
e = b
f = {(i.split(":")[0], i.split(":", 1)[1].strip()) for i in e}
g = sorted(f)
index = 0
print("{")
for k, v in g:
    print(repr(k).replace('\'','"'), repr(v).replace('\'','"'), sep=':', end=",\n")
print("}")
