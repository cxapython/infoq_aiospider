# -*- coding: utf-8 -*-
# @Time : 2019-01-28 14:41
# @Author : cxa
# @File : infoq_seed_spider.py
# @Software: PyCharm
import requests
import json
import time
import random
import datetime
from logger.log import crawler, storage
from db.mongo_helper import Mongo
import hashlib


class InfoQ_Seed_Spider():
    def __init__(self):
        self.start_url = "https://www.infoq.cn/public/v1/my/recommond"
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Content-Type": "application/json",
            "Host": "www.infoq.cn",
            "Origin": "https://www.infoq.cn",
            "Referer": "https://www.infoq.cn/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_req(self, data=None):
        '''
        请求列表页
        :param data:
        :return:
        '''
        req = self.session.post(self.start_url, data=json.dumps(data))
        if req.status_code in [200, 201]:
            return req

    def save_data(self, data):
        tasks = []
        for item in data:
            try:
                dic = {}
                uuid = item.get("uuid")
                dic["uuid"] = uuid
                dic["url"] = f"https://www.infoq.cn/article/{uuid}"
                title = item.get("article_title")
                dic["title"] = title
                dic["cover"] = item.get("article_cover")
                dic["summary"] = item.get("article_summary")
                author = item.get("author")
                if author:
                    dic["author"] = author[0].get("nickname")
                else:
                    dic["author"] = item.get("no_author", "").split(":")[-1]
                score = item.get("publish_time")
                dic["publish_time"] = datetime.datetime.utcfromtimestamp(score / 1000).strftime("%Y-%m-%d %H:%M:%S")
                dic["tags"] = ",".join([data.get("name") for data in item.get("topic")])
                translate = item.get("translator")
                dic["translator"] = dic["author"]
                if translate:
                    dic["translator"] = translate[0].get("nickname")
                dic["status"] = 0
                md5name = hashlib.md5(title.encode("utf-8")).hexdigest()  # 图片的名字
                dic["md5name"] = md5name
                dic["update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tasks.append(dic)
            except IndexError as e:
                crawler.error("解析出错")
        Mongo().save_data(tasks)
        crawler.info(f"add {len(tasks)} datas to mongodb")
        return score

    def start(self):
        i = 0
        post_data = {"size": 12}
        while i < 4:
            req = self.get_req(post_data)
            data = req.json().get("data")
            score = self.save_data(data)
            post_data.update({"score": score})
            i += 1
            time.sleep(random.randint(0, 5))


if __name__ == '__main__':
    iss = InfoQ_Seed_Spider()
    iss.start()
