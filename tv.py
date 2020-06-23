# -*- coding: UTF-8 -*-
import os
from datetime import datetime
import traceback
import logging
import subprocess
import time
import re
import threading
import json
import requests
import urllib
import urllib2
import lxml.html
from enum import Enum
from framework.common.daum import logger
from .logic import Logic
_REGEX_FILENAME = '^(?P<name>.*?)\\.E(?P<no>\\d+)(\\-E\\d{1,4})?\\.?(END\\.)?(?P<date>\\d{6})\\.(?P<etc>.*?)(?P<quality>\\d+)[p|P](\\-?(?P<release>.*?))?(\\.(.*?))?$'
_REGEX_FILENAME_NO_EPISODE_NUMBER = '^(?P<name>.*?)\\.(E(?P<no>\\d+)\\.?)?(END\\.)?(?P<date>\\d{6})\\.(?P<etc>.*?)(?P<quality>\\d+)[p|P](\\-?(?P<release>.*?))?(\\.(.*?))?$'
_REGEX_FILENAME_RENAME = '(?P<title>.*?)[\\s\\.]E?(?P<no>\\d{1,2})[\\-\\~\\s\\.]?E?\\d{1,2}'

class DaumTV:

    @staticmethod
    def check_filename(filename):
        logger.debug('check_filename filename : %s', filename)
        try:
            ret = None
            match1 = re.compile(_REGEX_FILENAME).match(filename)
            match2 = re.compile(_REGEX_FILENAME_NO_EPISODE_NUMBER).match(filename)
            for regex in [_REGEX_FILENAME, _REGEX_FILENAME_NO_EPISODE_NUMBER]:
                match = re.compile(regex).match(filename)
                if match:
                    logger.debug('QQQQQQQQQQQ')
                    ret = {}
                    ret['title'] = match1.group('name')
                    ret['no'] = match1.group('no')
                    ret['date'] = match1.group('date')
                    ret['etc'] = match1.group('etc').replace('.', '')
                    ret['quality'] = match1.group('quality')
                    ret['release'] = None
                    if 'release' in match1.groupdict():
                        ret['release'] = match1.group('release')
                    else:
                        ret['release'] = None
                    if ret['no'] is not None and ret['no'] != '':
                        ret['no'] = int(ret['no'])
                    else:
                        ret['no'] = -1
                    return DaumTV.change_filename_continous_episode(ret)

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

        return

    @staticmethod
    def change_filename_continous_episode(ret):
        try:
            if ret['title'].find(u'\ud569') == -1:
                return ret
            match = re.compile(_REGEX_FILENAME_RENAME).match(ret['title'])
            if match:
                logger.debug(u'\ud569\ubcf8 : %s', ret['filename'])
                ret['title'] = match.group('title').strip()
                if ret['no'] == -1:
                    ret['no'] = int(match.group('no'))
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_html(url):
        try:
            #from . import headers, cookies
            #res = Logic.session.get(url, headers=headers, cookies=cookies)
            from framework.common.daum import headers, session
            from system.logic_site import SystemLogicSite
            res = session.get(url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
            data = res.content
            return data
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_daum_tv_info(search_name, daum_id = None):
        try:
            entity = {}
            logger.debug('get_daum_tv_info 1 %s', search_name)
            search_name = DaumTV.get_search_name_from_original(search_name)
            logger.debug('get_daum_tv_info 2 %s', search_name)
            if daum_id is not None:
                url = 'https://search.daum.net/search?w=tv&q=%s&irk=%s&irt=tv-program&DA=TVP' % (urllib.quote(search_name.encode('utf8')), daum_id)
            else:
                url = 'https://search.daum.net/search?w=tv&q=%s' % urllib.quote(search_name.encode('utf8'))
            data = DaumTV.get_html(url)
            match = re.compile('irk\\=(?P<id>\\d+)').search(data)
            root = lxml.html.fromstring(data)
            daum_id = match.group('id') if match else ''
            entity = {}
            entity['daum_id'] = daum_id
            items = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/strong')
            if not items:
                return
            if len(items) == 1:
                entity['title'] = items[0].text.strip()
                entity['title'] = entity['title'].replace('?', '').replace(':', '')
            entity['status'] = 0
            items = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/span')
            if items:
                if items[0].text.strip() == u'\ubc29\uc1a1\uc885\ub8cc':
                    entity['status'] = 1
                elif items[0].text.strip() == u'\ubc29\uc1a1\uc608\uc815':
                    entity['status'] = 2
            items = root.xpath('//*[@id="tv_program"]/div[1]/div[3]/span')
            if items:
                entity['studio'] = items[0].text.strip()
                try:
                    entity['broadcast_info'] = items[1].text.strip()
                except:
                    pass

                try:
                    entity['broadcast_term'] = items[2].text.strip()
                except:
                    pass

                try:
                    items = root.xpath('//*[@id="tv_program"]/div[1]/div[2]/span')
                except:
                    pass

            try:
                match = re.compile('(\\d{4}\\.\\d{1,2}\\.\\d{1,2})~').search(entity['broadcast_term'])
                if match:
                    entity['start_date'] = match.group(1)
            except:
                pass

            items = root.xpath('//*[@id="tv_program"]/div[1]/dl[1]/dd')
            if len(items) == 1:
                entity['genre'] = items[0].text.strip().split(' ')[0]
                entity['genre'] = entity['genre'].split('(')[0].strip()
            items = root.xpath('//*[@id="tv_program"]/div[1]/dl[2]/dd')
            if len(items) == 1:
                entity['summary'] = items[0].text.replace('&nbsp', ' ')
            items = root.xpath('//*[@id="tv_program"]/div[1]/div[1]/a/img')
            if len(items) == 1:
                entity['poster_url'] = 'https:%s' % items[0].attrib['src']
            items = root.xpath('//*[@id="clipDateList"]/li')
            entity['episode_list'] = {}
            if len(items) > 300:
                items = items[len(items) - 300:]
            today = int(datetime.now().strftime('%Y%m%d'))
            for item in items:
                try:
                    a_tag = item.xpath('a')
                    if len(a_tag) == 1:
                        span_tag = a_tag[0].xpath('span[@class="txt_episode"]')
                        if len(span_tag) == 1:
                            if item.attrib['data-clip'] in entity['episode_list']:
                                if entity['episode_list'][item.attrib['data-clip']][0] == span_tag[0].text.strip().replace(u'\ud68c', ''):
                                    pass
                                else:
                                    idx = len(entity['episode_list'][item.attrib['data-clip']]) - 1
                                    _ = abs(int(entity['episode_list'][item.attrib['data-clip']][idx]) - int(span_tag[0].text.strip().replace(u'\ud68c', '')))
                                    if _ <= 4:
                                        if item.attrib['data-clip'] != '' and today >= int(item.attrib['data-clip']):
                                            entity['last_episode_date'] = item.attrib['data-clip']
                                            entity['last_episode_no'] = span_tag[0].text.strip().replace(u'\ud68c', '')
                                        entity['episode_list'][item.attrib['data-clip']].append(span_tag[0].text.strip().replace(u'\ud68c', ''))
                            else:
                                if item.attrib['data-clip'] != '' and today >= int(item.attrib['data-clip']):
                                    entity['last_episode_date'] = item.attrib['data-clip']
                                    entity['last_episode_no'] = span_tag[0].text.strip().replace(u'\ud68c', '')
                                entity['episode_list'][item.attrib['data-clip']] = [span_tag[0].text.strip().replace(u'\ud68c', '')]
                except Exception as e:
                    logger.error('Exception:%s', e)
                    logger.error(traceback.format_exc())

            try:
                if len(entity['episode_list']):
                    entity['episode_count_one_day'] = int(round(float(len(items)) / len(entity['episode_list'])))
                    if entity['episode_count_one_day'] == 0:
                        entity['episode_count_one_day'] = 1
                else:
                    entity['episode_count_one_day'] = 1
            except:
                entity['episode_count_one_day'] = 1

            entity['episode_list_json'] = json.dumps(entity['episode_list'])
            logger.debug('daum tv len(entity.episode_list) : %s %s %s', len(items), len(entity['episode_list']), entity['episode_count_one_day'])
            return entity
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

        return

    @staticmethod
    def get_search_name_from_original(search_name):
        search_name = search_name.replace('\xec\x9d\xbc\xec\x9d\xbc\xec\x97\xb0\xec\x86\x8d\xea\xb7\xb9', '').strip()
        search_name = search_name.replace('\xed\x8a\xb9\xeb\xb3\x84\xea\xb8\xb0\xed\x9a\x8d\xeb\x93\x9c\xeb\x9d\xbc\xeb\xa7\x88', '').strip()
        search_name = re.sub('\\[.*?\\]', '', search_name).strip()
        search_name = re.sub(u'^.{2,3}\ub4dc\ub77c\ub9c8', '', search_name).strip()
        search_name = re.sub(u'^.{1,3}\ud2b9\uc9d1', '', search_name).strip()
        return search_name

    @staticmethod
    def get_show_info(title, no = None, date = None):
        try:
            title = DaumTV.get_search_name_from_original(title)
            url = 'https://search.daum.net/search?q=%s' % urllib.quote(title.encode('utf8'))
            data = DaumTV.get_html(url)
            root = lxml.html.fromstring(data)
            home_info = DaumTV.get_show_info_on_home(root)
            tv = DaumTV.get_daum_tv_info(title)
            ret = {'home': home_info,
             'tv': tv}
            return ret
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_show_info_on_home(root):
        try:
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/a')
            if len(tags) < 1:
                return
            tag_index = len(tags) - 1
            entity = {}
            entity['title'] = tags[tag_index].text
            logger.debug('get_show_info_on_home title: %s', entity['title'])
            match = re.compile('q\\=(?P<title>.*?)&').search(tags[tag_index].attrib['href'])
            if match:
                entity['title'] = urllib.unquote(match.group('title'))
            entity['id'] = re.compile('irk\\=(?P<id>\\d+)').search(tags[tag_index].attrib['href']).group('id')
            entity['status'] = 1
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/span/span')
            if len(tags) == 1:
                if tags[0].text == u'\ubc29\uc1a1\uc885\ub8cc':
                    entity['status'] = 2
                elif tags[0].text == u'\ubc29\uc1a1\uc608\uc815':
                    entity['status'] = 0
            logger.debug('get_show_info_on_home status: %s', entity['status'])
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div')
            entity['extra_info'] = tags[0].text_content().strip()
            logger.debug('get_show_info_on_home extra_info: %s', entity['extra_info'])
            entity['studio'] = ''
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/a')
            if len(tags) == 1:
                entity['studio'] = tags[0].text
            else:
                tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span[1]')
                if len(tags) == 1:
                    entity['studio'] = tags[0].text
            logger.debug('get_show_info_on_home studio: %s', entity['studio'])
            tags = root.xpath('//*[@id="tvpColl"]/div[2]/div/div[1]/div/span')
            entity['extra_info_array'] = [ tag.text for tag in tags ]
            entity['broadcast_info'] = entity['extra_info_array'][-2].strip()
            entity['broadcast_term'] = entity['extra_info_array'][-1].split(',')[-1].strip()
            entity['year'] = re.compile('(?P<year>\\d{4})').search(entity['extra_info_array'][-1]).group('year')
            logger.debug('get_show_info_on_home 1: %s', entity['status'])
            entity['series'] = []
            entity['series'].append({'title': entity['title'],
             'id': entity['id'],
             'year': entity['year']})
            tags = root.xpath('//*[@id="tv_series"]/div/ul/li')
            if tags:
                try:
                    more = root.xpath('//*[@id="tv_series"]/div/div/a')
                    url = more[0].attrib['href']
                    if not url.startswith('http'):
                        url = 'https://search.daum.net/search%s' % url
                    logger.debug('MORE URL : %s', url)
                    if more[0].xpath('span')[0].text == u'\uc2dc\ub9ac\uc988 \ub354\ubcf4\uae30':
                        more_root = HTML.ElementFromURL(url)
                        tags = more_root.xpath('//*[@id="series"]/ul/li')
                except Exception as e:
                    logger.debug('Not More!')
                    logger.debug(traceback.format_exc())

                for tag in tags:
                    dic = {}
                    dic['title'] = tag.xpath('a')[0].text
                    dic['id'] = re.compile('irk\\=(?P<id>\\d+)').search(tag.xpath('a')[0].attrib['href']).group('id')
                    if tag.xpath('span'):
                        dic['date'] = tag.xpath('span')[0].text
                        dic['year'] = re.compile('(?P<year>\\d{4})').search(dic['date']).group('year')
                    else:
                        dic['year'] = None
                    entity['series'].append(dic)

                entity['series'] = sorted(entity['series'], key=lambda k: int(k['id']))
            logger.debug('SERIES : %s', len(entity['series']))
            entity['equal_name'] = []
            tags = root.xpath(u'//div[@id="tv_program"]//dt[contains(text(),"\ub3d9\uba85 \ucf58\ud150\uce20")]//following-sibling::dd')
            if tags:
                tags = tags[0].xpath('*')
                for tag in tags:
                    if tag.tag == 'a':
                        dic = {}
                        dic['title'] = tag.text
                        dic['id'] = re.compile('irk\\=(?P<id>\\d+)').search(tag.attrib['href']).group('id')
                    elif tag.tag == 'span':
                        match = re.compile('\\((?P<studio>.*?),\\s*(?P<year>\\d{4})?\\)').search(tag.text)
                        if match:
                            dic['studio'] = match.group('studio')
                            dic['year'] = match.group('year')
                        elif tag.text == u'(\ub3d9\uba85\ud504\ub85c\uadf8\ub7a8)':
                            entity['equal_name'].append(dic)
                        elif tag.text == u'(\ub3d9\uba85\ud68c\ucc28)':
                            continue

            logger.debug(entity)
            return entity
        except Exception as e:
            logger.debug('Exception get_show_info_by_html : %s', e)
            logger.debug(traceback.format_exc())

        return