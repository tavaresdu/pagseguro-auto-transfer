# -*- coding: utf-8 -*-
from scrapy import Spider, Item, Field
from scrapy.http.request import Request
from scrapy.http import FormRequest, HtmlResponse
from lxml import html
import datetime

class TransferItem(Item):
    user = Field()
    account = Field()
    value = Field()
    date = Field()

class PagseguroSpider(Spider):
    name = 'pagseguro_autotransf'

    def __init__(self, user, password, account):
        self.user = user
        self.password = password
        self.account = account

    def start_requests(self):
        yield Request(url='https://pagseguro.uol.com.br/acesso.jhtml',
                      callback=self.initial_parse,
                      dont_filter=True,
                      meta={'cookiejar':0})

    def initial_parse(self, response):
        token = response.xpath('//input[@name="acsrfToken"]/@value')[0].extract()
        skin = response.xpath('//input[@name="skin"]/@value')[0].extract()
        dest = response.xpath('//input[@name="dest"]/@value')[0].extract()

        data = {'acsrfToken': unicode(token),
                'skin': unicode(skin),
                'dest': unicode(dest),
                'user': unicode(self.user),
                'pass': unicode(self.password)}

        yield FormRequest(url=u'https://pagseguro.uol.com.br/login.jhtml',
                          callback=self.login_parse,
                          dont_filter=True,
                          formdata=data,
                          meta=response.meta)

    def login_parse(self, response):
        yield Request(url='https://pagseguro.uol.com.br//operations/viewWithdraw.jhtml',
                      dont_filter=True,
                      callback=self.transfer_parse,
                      meta=response.meta)

    def transfer_parse(self, response):
        data = {}
        for select in response.xpath('//form[@action="/operations/confirmWithdraw.jhtml"]//input[@value][@name][@type="hidden"]'):
            name = select.xpath('@name')[0].extract()
            value = select.xpath('@value')[0].extract()
            data[str(name)] = str(value)

        data['selectedAccount'] = self.account
        valueSelect = response.xpath('//*[@id="accountBalance"]/text()')
        data['value'] = str(valueSelect[0].extract()).replace('R$', '').strip()
        self.value = data['value']

        yield FormRequest(url='https://pagseguro.uol.com.br/operations/confirmWithdraw.jhtml',
                          dont_filter=True,
                          callback=self.confirm_parse,
                          formdata=data,
                          meta=response.meta)

    def confirm_parse(self, response):
        html_response = HtmlResponse(response.url, body=response.body)
        body = html_response.body_as_unicode().encode('utf8')

        if 'Esta solicitação de transferência será gratuita' in body:
            data = {'acsrfToken': response.xpath('//input[@name="acsrfToken"]/@value')[0].extract()}

            yield FormRequest(url='https://pagseguro.uol.com.br/operations/startWithdraw.jhtml',
                              dont_filter=True,
                              callback=self.success_parse,
                              formdata=data,
                              meta=response.meta)
        else:
            yield Request(url='https://pagseguro.uol.com.br/operations/changeWithdraw.jhtml',
                          dont_filter=True,
                          callback=self.logout_parse,
                          meta=response.meta)

    def success_parse(self, response):
        item = TransferItem()
        item['user'] = self.user
        item['account'] = self.account
        item['value'] = self.value
        item['date'] = datetime.datetime.now().isoformat()

        yield item

        yield Request(url='https://pagseguro.uol.com.br/logout.jhtml',
                      dont_filter=True,
                      meta=response.meta,
                      callback=self.final_parse)

    def logout_parse(self, response):
        yield Request(url='https://pagseguro.uol.com.br/logout.jhtml',
                      dont_filter=True,
                      meta=response.meta,
                      callback=self.final_parse)

    def final_parse(self, response):
        pass
