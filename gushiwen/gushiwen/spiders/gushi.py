# -*- coding: utf-8 -*-
import scrapy
import re
from w3lib.html import remove_tags


class GushiSpider(scrapy.Spider):
    name = 'gushi'
    domain = 'https://www.gushiwen.cn'
    #allowed_domains = ['https://www.gushiwen.org/shiwen/']
    start_urls = ['https://www.gushiwen.cn/shiwens/']
    n = 0

    def parse(self, response):
        # 提取分页参数url
        nextpage = response.css("form .pagesright .amore").css("a::attr(href)").extract()
        # 提取古诗文网的古诗详情页面url，此处会爬取到两类url，一类是古诗文，一类是作者，按照古诗文->作者 的顺序
        urls = response.css(".cont p a[target=_blank]").css("a::attr(href)").extract()
        print('urls------')
        # 分别拆分作者和诗文页面 url
        poetry_urls = [item for item in urls if 'shiwenv_' in item]
        author_urls = [item for item in urls if 'authorv' in item]
        # 针对古诗文的爬取
        for item in poetry_urls:
            print(self.domain + item)
            yield scrapy.Request(self.domain + item, callback=self.poet_parse)
        # 爬取下一个分页
        if nextpage and len(nextpage) > 0:
            print('进行下一个分页：' + nextpage[0])
            yield response.follow(self.domain + nextpage[0], callback=self.parse)

    # 诗文处理
    def poet_parse(self, response):
        itemDict = {}
        # 古诗详情页面存在多首古诗，所以需要提取第一个古诗的标题
        title = response.css('div.cont h1::text')[0].get()
        print('标题：' + title)
        ################################################################################################################
        # print('提取到的数据：-----author---------')
        # print("html："  + response.css(".cont .source a[href^='/author']")[0].extract())
        # print('作者：' + response.css("div.cont p.source a[href^='/author']::text")[1].get())
        # print('作者：（AI）' + response.css("div.cont p.source a[href^='/author']::text")[1].getall()[-1].strip())
        # print(response.css("div.cont p.source a[href^='/author']::text").getall())
        # 提取出标签 <a href='author_xxxx.aspx>/nxxxxx/n作者名</a>标签中的作者，因为在古诗页面有”猜你喜欢“页面可能还有其他推荐的古诗，所以只能获取authors[0]
        author_list = [text.strip() for text in response.css("div.cont p.source a[href^='/author']::text").getall() if
                       text.strip()]
        author = author_list[0]
        print('作者：' + author)
        # print('----------author------------------------')
        ################################################################################################################
        # print('提取到的数据：-----dynasty---------')
        # print('朝代：' + response.css("div.cont p.source a[href^='/shiwens/default.aspx?cstr=']::text")[0].get().strip("〔〕"))
        # print('----------dynasty------------------------')
        # 朝代提取，同样需要第一个元素
        dynasty = response.css("div.cont p.source a[href^='/shiwens/default.aspx?cstr=']::text")[0].get().strip("〔〕")
        ################################################################################################################
        # 古诗主体内容提取，已将所有非法字符如换行符/n、如html标签 <br>清洗掉
        content_list = [item.strip() for item in response.css("div.cont div.contson::text").getall() if item.strip() and item != '<br>']
        content = ''.join(content_list)
        # print("内容------------------")
        print(content)
        # print('all----------------')
        # print(content_list)
        # print('content--------------------')
        ################################################################################################################
        Tag = "暂无标签"
        if (response.css(".sons .tag").extract()):
            Tag = ""
            for tag in response.css(".sons .tag")[0].css("a").extract():
                Tag += re.findall(r">.+<", tag)[0][1:-1] + " "
        Id = ""
        Id1 = ""
        itemDict.update(
            {"name": title, "dynasty": dynasty, "author": author, "content": remove_tags(content), "tag": Tag})
        if (response.css(".left div[id^='fanyi']").extract()):
            Id = re.findall(r"fanyi\d+", response.css(".left div[id^='fanyi']").extract()[0])[0][5:]
        if (response.css(".left div[id^='shangxi']").extract()):
            Id1 = re.findall(r"shangxi\d+", response.css(".left div[id^='shangxi']").extract()[0])[0][7:]
        if (Id and Id1):
            request = scrapy.Request("https://so.gushiwen.org/shiwen2017/ajaxfanyi.aspx?id=" + Id, callback=self.yizhu)
            request.meta['id'] = Id1
            itemDict["tag2"] = "request1"
            request.meta['itemDict'] = itemDict
            yield request
        elif (Id):
            request = scrapy.Request("https://so.gushiwen.org/shiwen2017/ajaxfanyi.aspx?id=" + Id, callback=self.yizhu)
            itemDict["tag2"] = "request2"
            request.meta['itemDict'] = itemDict
            request.meta['id'] = Id1
            yield request
        elif (Id1):
            content = ""
            fanyi = "暂无翻译"
            zhushi = "暂无注释"
            if (response.css(".sons .contyishang").extract()):
                for item in response.css(".sons .contyishang")[0].css("p").extract():
                    content += item
                content = remove_tags(content.replace("<br>", "/n"))[4:]
                fanyi = content.split("注释")[0]
                zhushi = content.split("注释")[1]
            cankao = "暂无参考"
            temp = response.css(".cankao div span").extract()
            if (temp):
                cankao = ""
                for index in range(len(temp)):
                    cankao += remove_tags(temp[index])
                    if (index % 2 == 1):
                        cankao += "/n"
            itemDict.update({"fanyi": fanyi, "zhushi": zhushi, "cankao": cankao})
            request = scrapy.Request("https://so.gushiwen.org/shiwen2017/ajaxshangxi.aspx?id=" + Id1,
                                     callback=self.shangxi)
            itemDict["tag2"] = "request3"
            request.meta['itemDict'] = itemDict
            yield request
        else:
            content = ""
            fanyi = "暂无翻译"
            zhushi = "暂无注释"
            if (response.css(".sons .contyishang").extract()):
                for item in response.css(".sons .contyishang")[0].css("p").extract():
                    content += item
                content = remove_tags(content.replace("<br>", "/n"))[4:]
                fanyi = content.split("注释")[0]
                zhushi = content.split("注释")[1]
            cankao = "暂无参考"
            temp = response.css(".cankao div span").extract()
            if (temp):
                cankao = ""
                for index in range(len(temp)):
                    cankao += remove_tags(temp[index])
                    if (index % 2 == 1):
                        cankao += "/n"
            self.n += 1
            itemDict.update({"fanyi": fanyi, "zhushi": zhushi, "cankao": cankao, "shangxi": "暂无赏析", "n": self.n})
            itemDict["tag2"] = "request4"
            yield itemDict

    # 译注处理
    def yizhu(self, response):
        Id = response.meta['id']
        itemDict = response.meta['itemDict']
        content = ""
        fanyi = "暂无翻译"
        zhushi = "暂无注释"
        if (response.css(".sons .contyishang").extract()):
            fanyi = ""
            zhushi = ""
            for item in response.css(".contyishang p").extract():
                content += item
            content = remove_tags(content.replace("<br>", "/n"))[4:]
        if (content):
            fanyi = content.split("注释")[0]
            zhushi = content.split("注释")[1]
        #fanyi=remove_tags(response.css(".contyishang p").extract()[0].replace("<br>","/n"))[4:]
        #zhushi=remove_tags(response.css(".contyishang p").extract()[1].replace("<br>","/n"))[4:]
        temp = response.css(".cankao div span").extract()
        cankao = "暂无参考"
        if (temp):
            cankao = ""
            for index in range(len(temp)):
                cankao += remove_tags(temp[index])
                if (index % 2 == 1):
                    cankao += "/n"
        itemDict.update({"fanyi": fanyi, "zhushi": zhushi, "cankao": cankao})
        if (Id):
            request = scrapy.Request("https://so.gushiwen.org/shiwen2017/ajaxshangxi.aspx?id=" + Id,
                                     callback=self.shangxi)
            request.meta['itemDict'] = itemDict
            yield request
        else:
            self.n += 1
            itemDict.update({"shangxi": "暂无赏析", "n": self.n})
            yield itemDict
        #print("FANYI",fanyi)

    # 赏析处理
    def shangxi(self, response):
        itemDict = response.meta['itemDict']
        temp = response.css(".contyishang p").extract()
        shangxi = "暂无赏析"
        if (temp):
            shangxi = ""
            for item in temp:
                shangxi += remove_tags(item.replace("</p>", "/n"))
        self.n += 1
        itemDict.update({"shangxi": shangxi, "n": self.n})
        # print("PoetPPPPPP",str(itemDict))

        yield itemDict
