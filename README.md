### 异步爬虫模块aiohttp实战之infoq
> 之前写过很多的关于异步的文章，介绍了asyncio的使用，大多的只是通过简单的例子说明了asyncio的使用，但是没有拿出具体的使用例子，所以这次特意用一个具体例子来说明异步模块aiohttp配合asyncio的使用。

这次以infoq网站为例子进行讲解，infoq是一个怎样的网站，这里引用官网的一句话
「InfoQ 是一个实践驱动的社区资讯站点,致力于促进软件开发领域知识与创新的传播。... InfoQ 每周精要 订阅InfoQ 每周精要,加入资深开发者汇聚的庞大技术社区。」 很明显了infoq是一个技术型的网站，这次我们就对该网站的推荐内容进行讲解。
###思路分析
这里先说下思路，这里分了两步，首先爬取列表页，然后再去爬详情页的内容。
爬取列表页的数据保存到数据库,这里我使用的是mongodb，同时加一个字段标注状态，这个状态是为了后面详情页可以做到一个续爬，这里我设置三种状态0,1,2其中0表示初始状态也就是还没开始爬，1表示开始下载，2表示下载成功。通过状态我们可以直到已经完成了多少链接的爬取了。进而达到的一个续爬的效果。爬取详情页的时候就去读取数据库中状态为0的数据。根据状态码我们就可以作出对应的操作了，例如我们任务都完了，查看列表页的数据发现状态是1，可以知道这个爬取的过程中出现了问题，所以我们将状态改为0，再运行详情页的程序即可。
### 网站分析之列表部分
首先让我分析一下，这个推荐内容部分都有哪些请求，经过查看发现在链接https://www.infoq.cn/public/v1/my/recommond 里面有我们需要的内容
很明显这是一个ajax请求的页面，然后就是分析这个链接的请求方式和请求参数了
请求链接我们已经知道了，然后看请求参数部分经过观察我们发现请求参数的格式为
```
{"size":12,"score":1549328400000}
```
然后我们只要直到参数来源就好了,一般通过多翻几页去总结规律，观察发现size的值都是12，也就是一页显示的内容，然后是score内容，我们发现每一页的score内容是不同的，通过搜索 可以发现再上一页的json内容中包含着这个字段。
![](https://img2018.cnblogs.com/blog/736399/201902/736399-20190207174247059-348757324.gif)
于是我们就可以写代码了。
### 列表部分的代码
因为列表页部分是一步接一步的不适合并发所以我们用requests模块常规的方式爬取即可。
文件名infoq_seed_spider.py
网络请求部分
```python
    def get_req(self, data=None):
        req = self.session.post(self.start_url, data=json.dumps(data))
        if req.status_code in [200, 201]:
            return req
```
数据解析部分
```
def save_data(self, data):
        tasks = []
        for item in data:
            try:
                dic = {}
                uuid = item.get("uuid")
                dic["uuid"] = uuid# 经过分析发现uuid就是详情页链接的组成部分。
                dic["url"] = f"https://www.infoq.cn/article/{uuid}"
                dic["title"] = item.get("article_title")
                dic["cover"] = item.get("article_cover")
                dic["summary"] = item.get("article_summary")
                author=item.get("author")
                if author:
                   dic["author"] = author[0].get("nickname")
                else:
                   dic["author"]=item.get("no_author","").split(":")[-1]
                score=item.get("publish_time")
                dic["publish_time"] = datetime.datetime.utcfromtimestamp(score/1000).strftime("%Y-%m-%d %H:%M:%S")
                dic["tags"] = ",".join([data.get("name") for data in item.get("topic")])
                translate = item.get("translator")
                dic["translator"] = dic["author"]
                if translate:
                    dic["translator"] = translate[0].get("nickname")
                dic["status"] = 0
                dic["update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                tasks.append(dic)
            except IndexError as e:
                crawler.error("解析出错")
        Mongo().save_data(tasks)
        crawler.info(f"add {len(tasks)} datas to mongodb")
        return score
```
程序入口
```python
    def start(self):
        i = 0
        post_data = {"size": 12} 
        while i < 10: #这里只爬取了10页，这个值可以自己设置
            req = self.get_req(post_data)
            data = req.json().get("data")
            score = self.save_data(data)
            post_data.update({"score": score}) #通过上一页的内容得知下一次要请求的参数。
            i += 1
            time.sleep(random.randint(0, 5))

```
列表页逻辑简单代码也是同步，就没有什么需要强调的地方了
新手需要注意是访问量和频率，这里只是做一个学习范例所以请求量和请求频率相应的比较低。
###网站分析之详情部分
这里分为两部分存储，一个是详情内容的封面我将图片保存到了本地。另外一个就是详情内容的爬取保存到数据库里，保存图片的同时获取图片的路径一起保存在数据库，方便找到文章的配图。
### 详情页的思考
一开始我以为详情页的内容请求类似https://www.infoq.cn/article/cY3lZj1G-cR2iJ3ONUd6链接就行了，但是后来事实证明我想简单了，详情页其实也是通过ajax加载的，经过和列表页类似的分析，发现请求链接为：https://www.infoq.cn/public/v1/article/getDetail，请求参数为 uuid,也就是详情页的链接后面的部分，我们在爬取列表页的时候已经获取了。
也就是说详情页的爬虫我们是通过访问数据库的形式去进行爬取的，这里我们就可以做到并发去访问了。这里就让我们熟悉一下aiohttp的使用已经其他异步库的使用。
###详情页的代码部分
首先说下我们需要的包,aiohttp异步网络请求包,motor异步mongodb请求包,aiofiles异步文件操作包,async_timeout请求timeout设置包。以上包我们都可以通过pip进行安装，下面我们对这些包进行一一了解。
#### 数据读取
首先我们需要读取数据的数据，这里我们使用pymongo。
首先是导入必备的包pip install pymongo安装即可。
读取部分没有涉及太多的操作，我们就直接获取一个生成器格式的数据即可
```
def find_data(self, col="infoq_seed"):
        # 获取状态为0的数据
        data = self.db[col].find({"status": 0})
        gen = (item for item in data)
        return gen
```
#### 入口函数
```
async def run(data):
    crawler.info("Start Spider")
    async with aiohttp.connector.TCPConnector(limit=300, force_close=True, enable_cleanup_closed=True) as tc:  #限制tcp连接数
        async with aiohttp.ClientSession(connector=tc) as session: #创建一个可持续链接的session，传递下去，
            coros = (asyncio.ensure_future(bound_fetch(item, session)) for item in data) 
            await start_branch(coros) 
```
#### 协程分流
这里主要做一个任务的均分，对于同步中的迭代器我们可以使用itertools的islice模块来实现
```
# -*- coding: utf-8 -*-
# @Time : 2019/1/2 11:52 AM
# @Author : cxa
# @File : 切片.py
# @Software: PyCharm
from itertools import islice

la = (x for x in range(20))
print(type(la))
for item in islice(la, 5, 9):  # 取下标5-9的元素
    print(item)
```
但是异步生成器没有这中方法所以定义了如下方式进行分流。
下面代码的作用就是每次并发10个。通过修改limited_as_completed
方法的第二个参数可以设置不同的并发量。
```
async def start_branch(tasks):
    # 分流
    [await _ for _ in limited_as_completed(tasks, 10)]


async def first_to_finish(futures, coros):
    while True:
        await asyncio.sleep(0.01)
        for f in futures:
            if f.done():
                futures.remove(f)
                try:
                    new_future = next(coros)
                    futures.append(asyncio.ensure_future(new_future))
                except StopIteration as e:
                    pass
                return f.result()


def limited_as_completed(coros, limit):
    futures = [asyncio.ensure_future(c) for c in islice(coros, 5, limit)]

    while len(futures) > 0:
        yield first_to_finish(futures, coros)
```
一般对于并发100万以及更大的数据量时，可以使用此方案。
下面具体说下网络请求部分的逻辑。
#### 网络请求
这里分了两部分进行并行抓取，图片部分和详情内容部分
```
async def bound_fetch(item, session):
    md5name = item.get("md5name")
    file_path = os.path.join(os.getcwd(), "infoq_cover")
    image_path = os.path.join(file_path, f"{md5name}.jpg")

    item["md5name"] = md5name
    item["image_path"] = image_path
    item["file_path"] = file_path
    async with sema:
        await fetch(item, session) #内容抓取部分协程
        await get_buff(item, session) #图片抓去部分协程
```
内容部分核心内容
```
async def fetch(item, session, retry_index=0):
    try:
        refer = item.get("url")
        name = item.get("title")
        uuid = item.get("uuid")
        md5name = hashlib.md5(name.encode("utf-8")).hexdigest()  # 图片的名字
        item["md5name"] = md5name
        data = {"uuid": uuid}
        headers["Referer"] = refer
        if retry_index == 0:
            await MotorBase().change_status(uuid, item, 1)  #开始下载并修改列表页的状态
        with async_timeout.timeout(60):
            async with session.post(url=base_url, headers=headers, data=json.dumps(data)) as req:
                res_status = req.status

                if res_status == 200:
                    jsondata = await req.json()
                    await get_content(jsondata, item) #获取内容
        await MotorBase().change_status(uuid, item, 2)  #修改状态下载成功
    except Exception as e:
        jsondata = None
    if not jsondata:
        crawler.error(f'Retry times: {retry_index + 1}')
        retry_index += 1
        return await fetch(item, session, retry_index) 
```
图片抓取部分核心内容
```
async def get_buff(item, session):
    url = item.get("cover")
    with async_timeout.timeout(60):
        async with session.get(url) as r:
            if r.status == 200:
                buff = await r.read()
                if len(buff):
                    crawler.info(f"NOW_IMAGE_URL:, {url}")
                    await get_img(item, buff)
```
#### 数据库的异步读取操作
首先导入mongo的异步库motor。
```
from motor.motor_asyncio import AsyncIOMotorClient
```
然后创建数据库链接
```
class MotorBase():
    def __init__(self):
        self.__dict__.update(**db_configs)
        if self.user:
            self.motor_uri = f"mongodb://{self.user}:{self.passwd}@{self.host}:{self.port}/{self.db_name}?authSource={self.user}"
        self.motor_uri = f"mongodb://{self.host}:{self.port}/{self.db_name}"
        self.client = AsyncIOMotorClient(self.motor_uri)
        self.db = self.client.spider_data
```
 上面的代码可以根据是否需要用户名来创建不同的链接方式
其中读取的配置内容格式如下
```
# 数据库基本信息
db_configs = {
    'type': 'mongo',
    'host': '127.0.0.1',
    'port': '27017',
    "user": "",
    "password": "",
    'db_name': 'spider_data'
}
```
状态修改
```
 async def change_status(self, uuid, item, status_code=0):
        # status_code 0:初始,1:开始下载，2下载完了
        try:
            # storage.info(f"修改状态,此时的数据是:{item}")
            item["status"] = status_code
            await self.db.infoq_seed.update_one({'uuid': uuid}, {'$set': item}, upsert=True)
        except Exception as e:
            if "immutable" in e.args[0]:
                await self.db.infoq_seed.delete_one({'_id': item["_id"]})
                storage.info(f"数据重复删除:{e.args},此时的数据是:{item}")
            else:
                storage.error(f"修改状态出错:{e.args}此时的数据是:{item}")
```
数据保存
```
 async def save_data(self, item):
        try:
            await self.db.infoq_details.update_one({
                'uuid': item.get("uuid")},
                {'$set': item},
                upsert=True)
        except Exception as e:
            storage.error(f"数据插入出错:{e.args}此时的item是:{item}")
```
图片保存
```
async def get_img(item, buff):
    # 题目层目录是否存在
    file_path = item.get("file_path")
    image_path = item.get("image_path")
    if not os.path.exists(file_path):
        os.makedirs(file_path)

    # 文件是否存在
    if not os.path.exists(image_path):
        storage.info(f"SAVE_PATH:{image_path}")
        async with aiofiles.open(image_path, 'wb') as f:
            await f.write(buff)
```
motor,aiofiles的使用类似pymongo,os.open只不过使用async/await关键字实现而已.
