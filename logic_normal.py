# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import datetime
import traceback
import threading
import re
import subprocess
import shutil
import time
import urllib
import rclone
import daum_tv

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from guessit import guessit

# sjva 공용
from framework import app, db, scheduler, path_app_root, celery
from framework.job import Job
from framework.util import Util
from system.model import ModelSetting as SystemModelSetting

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelMediaItem


#########################################################
class LogicNormal(object):

    @staticmethod
    @celery.task
    def scheduler_function():
        try:
            logger.debug("파일정리 시작!")
            source_base_path = ModelSetting.get_setting_value('source_base_path')
            ktv_base_path = ModelSetting.get_setting_value('ktv_base_path')
            movie_base_path = ModelSetting.get_setting_value('movie_base_path')
            error_path = ModelSetting.get_setting_value('error_path')
            interval = ModelSetting.get('interval')
            emptyFolderDelete = ModelSetting.get('emptyFolderDelete')

            source_base_path = [ x.strip() for x in source_base_path.split(',') ]
            if not source_base_path:
                return None
            if None == '':
                return None

            try:
                fileList = LogicNormal.make_list(source_base_path, ktv_base_path, movie_base_path, error_path)
                time.sleep(int(interval))

            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def item_list(path, f):
        try:
            item = {}
            item['path'] = path
            item['name'] = f
            item['fullPath'] = os.path.join(path, f)
            item['guessit'] = guessit(f)
            item['ext'] = os.path.splitext(f)[1].lower()
            item['search_name'] = None
            match = re.compile('^(?P<name>.*?)[\\s\\.\\[\\_\\(]\\d{4}').match(item['name'])
            logger.debug('ml - match: %s', match)
            if match:
                item['search_name'] = match.group('name').replace('.', ' ').strip()
                logger.debug('ml 1 - item[search_name]: %s', item['search_name'])
                item['search_name'] = re.sub('\\[(.*?)\\]', '', item['search_name'])
                logger.debug('ml 2 - item[search_name]: %s', item['search_name'])
            #else:
                #item['search_name'] = item['title']
                #logger.debug('ml - search_name: %s', item['search_name'])
            if LogicNormal.isHangul(item['name']) > 0:
                item['search_name'] = f

            return item

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def make_list(source_path, ktv_path, movie_path, err_path):
        try:
            for path in source_path:
                logger.debug('path:%s', path)
                lists = os.listdir(path.strip())
                for f in lists:
                    try:
                        if LogicNormal.isHangul(str(f)) > 0:
                            f = f.encode('utf-8')
                        p = os.path.join(path.strip(), f)
                        logger.debug('p:%s', p)
                        if os.path.isfile(p):
                            item = LogicNormal.item_list(p, f)
                            lists.append(item)
                            LogicNormal.check_move_list(item, ktv_path, movie_path, err_path)

                            if ModelSetting.get_bool('emptyFolderDelete'):
                                lists.reverse()
                                for item in lists:
                                    logger.debug( "dir_path : " + item['fullPath'])
                                    if source_path != item['fullPath'] and len(os.listdir(item['fullPath'])) == 0:
                                        os.rmdir(unicode(item['fullPath']))

                        elif os.path.isdir(p):
                            sub_lists = os.listdir(p)
                            for fs in sub_lists:
                                try:
                                    if LogicNormal.isHangul(str(fs)) > 0:
                                        fs = fs.encode('utf-8')
                                    logger.debug('sub path:%s', os.path.join(p.strip(), fs))
                                    if os.path.isfile(os.path.join(p.strip(), fs)):
                                        item = LogicNormal.item_list(p, fs)
                                        sub_lists.append(item)
                                        LogicNormal.check_move_list(item, ktv_path, movie_path, err_path)

                                        if ModelSetting.get_bool('emptyFolderDelete'):
                                            sub_lists.reverse()
                                            for item in sub_lists:
                                                logger.debug( "dir_path : " + item['fullPath'])
                                                if source_path != item['fullPath'] and len(os.listdir(item['fullPath'])) == 0:
                                                    os.rmdir(unicode(item['fullPath']))

                                except Exception as e:
                                    logger.error('Exxception:%s', e)
                                    logger.error(traceback.format_exc())

                    except Exception as e:
                        logger.error('Exxception:%s', e)
                        logger.error(traceback.format_exc())

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def check_move_list(item, ktv_target_path, movie_target_path, error_target_path):
        try:
            #TV
            if 'episode' in item['guessit'] > 0:
                logger.debug('cml - drama ' + item['guessit']['title'])
                logger.debug('cml - drama condition not not ok ' + item['guessit']['title'])
                LogicNormal.move_except(item, error_target_path)
                '''
                daum_tv_info = daum_tv.Logic.get_daum_tv_info(item['guessit']['title'])
                if daum_tv_info is not None:
                    #logger.debug('cml - daum_tv_info[countries]: %s', daum_tv_info['countries'])
                    #for country in daum_tv_info['countries']:
                        #item['country'] = daum_tv_info.countries.add(country.strip())
                    #logger.debug('cml - item[country]: %s', item['country'])
                    #if 'country' in item['country'] == u'한국':
                    logger.debug('cml - drama condition ok ' + item['guessit']['title'])
                    LogicNormal.set_ktv(item, daum_tv_info)
                    LogicNormal.move_ktv(item, daum_tv_info, ktv_target_path)
                    #else:
                        #logger.debug('cml - drama condition not ok ' + item['name'])
                        #LogicNormal.move_except(item, error_target_path)
                else:
                    logger.debug('cml - drama condition not not ok ' + item['guessit']['title'])
                    LogicNormal.move_except(item, error_target_path)
                '''
            #Movie
            else:
                logger.debug('cml - movie ' + item['name'])
                rules = ['4K', '4k', 'UHD', '2160p', '2160P']
                for keywords in rules:
                    gregx = re.compile(keywords, re.I)
                    if (gregx.search(item['name'])) is not None:
                        logger.debug('cml - uhd condition match %s : %s', keywords, item['name'])
                        LogicNormal.move_except(item, error_target_path)
                        return

                logger.debug('cml - uhd condition not match %s : %s', keywords, item['name'])
                #if LogicNormal.isHangul(item['name']) is False:
                if 'year' in item['guessit']:
                    year = item['guessit']['year']
                    logger.debug('cml - movie year %s', year)
                    (item['is_include_kor'], daum_movie_info) = daum_tv.MovieSearch.search_movie(item['search_name'], item['guessit']['year'])
                    logger.debug('cml - movie ' + item['name'] + '' + item['search_name'])
                    if daum_movie_info and daum_movie_info[0]['score'] == 100:
                        #item['movie'] = movie[0]
                        logger.debug('cml - movie condition ok ' + item['name'])
                        LogicNormal.set_movie(item, daum_movie_info[0])
                        LogicNormal.move_movie(item, daum_movie_info[0], movie_target_path)
                    else:
                        logger.debug('cml - movie condition not ok ' + item['name'])
                        LogicNormal.move_except(item, error_target_path)
                else:
                    logger.debug('cml - movie condition not not ok ' + item['name'])
                    LogicNormal.move_except(item, error_target_path)
                '''
                else:
                    logger.debug('cml - movie is hangul ' + item['name'])
                    (item['is_include_kor'], daum_movie_info) = daum_tv.MovieSearch.search_movie(item['search_name'], 2020)
                    logger.debug('cml - movie ' + item['name'] + item['search_name'])
                    if daum_movie_info and daum_movie_info[0]['score'] == 100:
                        LogicNormal.set_movie(item, daum_movie_info[0])
                LogicNormal.move_movie(item, daum_movie_info[0], movie_target_path)                '''

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def set_ktv(data, ktv):
        try:
            data['ktv'] = ktv
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', ktv.title).replace('  ', ' '))
            folder_rule = ModelSetting.get_setting_value('folder_rule')
            tmp = folder_rule.replace('%TITLE%', ktv.title).replace('%GENRE%', ktv.genre)
            tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
            data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def set_movie(data, movie):
        try:
            data['movie'] = movie
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', movie['title']).replace('  ', ' '))
            if 'more' in movie:
                folder_rule = ModelSetting.get_setting_value('folder_rule')
                tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title']).replace('%COUNTRY%', movie['more']['country']).replace('%GENRE%', movie['more']['genre']).replace('%DATE%', movie['more']['date']).replace('%RATE%', movie['more']['rate']).replace('%DURING%', movie['more']['during'])
                tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
                data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv(data, info, base_path):
        try:
            logger.debug('=== title %s', data['dest_folder_name'])
            set_cat = u'드라마'
            set_country = u'한국'
            title = data['dest_folder_name']
            fullPath = data['fullPath']
            dest_folder_path = os.path.join(base_path.strip(), set_cat.encode('utf-8'), set_country.encode('utf-8'), title.encode('utf-8'))
            logger.debug('mk - dest_folder_path: %s', dest_folder_path)
            if not os.path.isdir(dest_folder_path):
                os.makedirs(dest_folder_path)
            shutil.move(fullPath.encode('utf-8'), dest_folder_path)
            LogicNormal.db_save(data, dest_folder_path)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_except(data, base_path):
        try:
            dest_folder_path = os.path.join(base_path.strip())
            logger.debug('me - move exception %s' , data['search_name'])
            #if not os.path.isdir(dest_folder_path):
            #    os.makedirs(dest_folder_path)
            #shutil.move(data['fullPath'], dest_folder_path)
            #LogicNormal.db_save(data, dest_folder_path)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_movie(data, info, base_path):
        try:
            set_country = []
            set_year = []
            condition = 0
            '''
            logger.debug('mm - info[more][info]: %s', info['more']['info'])
            keywords = ''.join(info['more']['info'])

            for words in keywords.split('|'):
                if u'에니메이션' in words:
                    logger.debug('mm - ani condition match : %s', words)
                    condition = 1
                else:
                    logger.debug('mm - ani not condition match : %s', words)
                    condition = 0

            if condition == 1:
                set_cat = u'애니메이션'
                target = u'극장판'
                dest_folder_path = os.path.join(base_path.strip(), set_cat.encode('utf-8'), target.encode('utf-8'), data['dest_folder_name'])
            '''

            logger.debug('mm - info[more][country]: %s', info['more']['country'])
            if u'한국' in info['more']['country']:
                set_country = u'한국'
            elif u'중국' in info['more']['country']:
                set_country = u'중국'
            elif u'홍콩' in info['more']['country']:
                set_country = u'중국'
            elif u'대만' in info['more']['country']:
                set_country = u'중국'
            elif u'일본' in info['more']['country']:
                set_country = u'일본'
            else:
                set_country = u'외국'

            logger.debug('mm - info[year]: %s', info['year'])
            if int(info['year']) < 1990:
                set_year = u'1900s'
            elif int(info['year']) >= 1990 and int(info['year']) < 2000:
                set_year = u'1990s'
            elif int(info['year']) >= 2000 and int(info['year']) < 2010:
                set_year = u'2000s'
            elif int(info['year']) >= 2010 and int(info['year']) <= 2012:
                set_year = u'~2012'
            elif int(info['year']) == 2013:
                set_year = u'2013'
            elif int(info['year']) == 2014:
                set_year = u'2014'
            elif int(info['year']) == 2015:
                set_year = u'2015'
            elif int(info['year']) == 2016:
                set_year = u'2016'
            elif int(info['year']) == 2017:
                set_year = u'2017'
            elif int(info['year']) == 2018:
                set_year = u'2018'
            elif int(info['year']) == 2019:
                set_year = u'2019'
            else:
                set_year = u'2020'
            set_cat = u'영화'
            dest_folder_path = os.path.join(base_path.strip(), set_cat.encode('utf-8'), set_country.encode('utf-8'), set_year.encode('utf-8'), data['dest_folder_name'])

            logger.debug('mm - dest_folder_path: %s', dest_folder_path)
            logger.debug('mm - fullPath: %s', data['fullPath'])
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(base_path.strip(), set_cat.encode('utf-8'), set_country.encode('utf-8'), set_year.encode('utf-8'), data['dest_folder_name'], data['name'])
            logger.debug('mm - fileCheck: %s', fileCheck)
            os.rename(data['fullPath'], fileCheck)
            #shutil.move(data['fullPath'], dest_folder_path)
            #if not os.path.isfile(fileCheck):
                #os.rename(data['fullPath'], fileCheck)
                #LogicNormal.db_save(data, dest_folder_path)
            #fileCheck = os.path.join(base_path.strip(), set_cat.encode('utf-8'), set_country.encode('utf-8'), set_year.encode('utf-8'), data['name'])
            #if not os.path.isfile(fileCheck):
                #shutil.move(data['fullPath'], dest_folder_path)
                #dest_folder_path = os.path.join(dest_folder_path.strip(), '/')

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def db_save(data, dest):
        try:
            entity = {}
            entity['name'] = data['search_name']
            entity['fileName'] = data['name']
            entity['dirName'] = data['fullPath']
            entity['targetPath'] = dest
            ModelMediaItem.save_as_dict(entity)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def search(values, searchFor):
        searchFor.encode('utf-8')
        for k in values:
            for v in values[k]:
                if searchFor in v:
                    return k
        return None

    @staticmethod
    def isHangul(text):

        if type(text) is not unicode:
            encText = text.decode('utf-8')
        else:
            encText = text

        hanCount = len(re.findall(u'[\u3130-\u318F\uAC00-\uD7A3]+', encText))

        return hanCount > 0

    @staticmethod
    def strip_all(x):

      if isinstance(x, str): # if using python2 replace str with basestring to include unicode type
        x = x.strip()
      elif isinstance(x, list):
        x = [LogicNormal.strip_all(v) for v in x]
      elif isinstance(x, dict):
        for k, v in x.iteritems():
          x.pop(k)  # also strip keys
          x[ LogicNormal.strip_all(k) ] = LogicNormal.strip_all(v)

      return x


