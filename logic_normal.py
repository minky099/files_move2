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
import json
import ast
import time
import urllib
import rclone
#import daum_tv

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from guessit import guessit

# sjva 공용
from framework import app, db, scheduler, path_app_root, celery
from framework.job import Job
from framework.util import Util
from system.model import ModelSetting as SystemModelSetting
from framework.logger import get_logger

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem

#from framework.common.daum import DaumTV
#########################################################
class LogicNormal(object):

    @staticmethod
    @celery.task
    def scheduler_function():
        try:
            logger.debug("파일정리 시작!")
            source_base_path = ModelSetting.get('source_base_path')
            ktv_drama_base_path = ModelSetting.get('ktv_drama_base_path')
            ktv_show_base_path = ModelSetting.get('ktv_show_base_path')
            movie_base_path = ModelSetting.get('movie_base_path')
            error_path = ModelSetting.get('error_path')
            source_base_path = [ x.strip() for x in source_base_path.split(',') ]
            if not source_base_path:
                return None
            if None == '':
                return None
            try:
                fileList = LogicNormal.make_list(source_base_path, ktv_drama_base_path, ktv_show_base_path, movie_base_path, error_path)
                if ModelSetting.get_bool('emptyFolderDelete'):
                    LogicNormal.empty_folder_remove(source_base_path)
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
            temp = re.sub('(s|S)+\d\d', '', f)
            #logger.debug('il1 - %s : %s', item['name'], temp)
            temp = re.sub('\-\d\d', '', temp)
            #logger.debug('il2 - %s : %s', item['name'], temp)
            temp = re.sub(u'\d?\d-\d?\d회 ?합?본?', '', temp)
            #logger.debug('il3 - %s : %s', item['name'], temp)
            item['guessit'] = guessit(temp)
            item['ext'] = os.path.splitext(f)[1].lower()
            item['search_name'] = None
            item['uhd'] = 0
            match = re.compile('^(?P<name>.*?)[\\s\\.\\[\\_\\(]\\d{4}').match(item['name'])
            if match:
                item['search_name'] = match.group('name').replace('.', ' ').strip()
                item['search_name'] = re.sub('\\[(.*?)\\]', '', item['search_name'])
            else:
                return None
            if LogicNormal.isHangul(item['search_name']) > 0:
                str = unicode(item['search_name'])
                item['search_name'] = str
            logger.debug('il4 - search_name:%s', item['search_name'])
            return item
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def make_list(source_path, ktv_drama_path, ktv_show_path, movie_path, err_path):
        interval = ModelSetting.get('interval')
        try:
            for path in source_path:
                logger.debug('path:%s', path)
                lists = os.listdir(path.strip())
                for f in lists:
                    try:
                        if LogicNormal.isHangul(str(f)) > 0:
                            f = f.encode('utf-8')
                        #f = str(f).strip()
                        p = os.path.join(path.strip(), f)
                        logger.debug('p:%s', p)

                        if os.path.isfile(p):
                            item = LogicNormal.item_list(path, f)
                            if item is not None:
                                LogicNormal.check_move_list(item, ktv_drama_path, ktv_show_path, movie_path, err_path)
                        elif os.path.isdir(p):
                            sub_lists = os.listdir(p)
                            for fs in sub_lists:
                                try:
                                    if LogicNormal.isHangul(str(fs)) > 0:
                                        fs = fs.encode('utf-8')
                                    #fs = str(fs).strip()
                                    if os.path.isfile(os.path.join(p.strip(), fs)):
                                        item = LogicNormal.item_list(p, fs)
                                        if item is not None:
                                            LogicNormal.check_move_list(item, ktv_drama_path, ktv_show_path, movie_path, err_path)
                                except Exception as e:
                                    logger.error('Exxception:%s', e)
                                    logger.error(traceback.format_exc())
                    except Exception as e:
                        logger.error('Exxception:%s', e)
                        logger.error(traceback.format_exc())
            time.sleep(int(interval))
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def check_move_list(item, ktv_drama_target_path, ktv_show_target_path, movie_target_path, error_target_path):
        ktv_show_genre_flag = ModelSetting.get_bool('ktv_show_genre_flag')
        try:
            rules = ['4K', '4k', 'UHD', '2160p', '2160P']
            condition = 0
            #TV
            if 'episode' in item['guessit'] > 0 and item['guessit']['type'] == 'episode':
                from framework.common.daum import DaumTV
                logger.debug('cml - drama %s, %s', item['name'], item['search_name'])
                for keywords in rules:
                    gregx = re.compile(keywords, re.I)
                    if (gregx.search(item['name'])) is not None:
                        item['uhd'] += 1

                daum_tv_info = DaumTV.get_daum_tv_info(item['guessit']['title'])
                #daum_tv_info = DaumTV.get_daum_tv_info(item['search_name'])
                if daum_tv_info is not None:
                    if daum_tv_info['genre'] == u'드라마':
                        logger.debug('cml - korea drama %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_drama(item, daum_tv_info, ktv_drama_target_path)
                    elif ktv_show_genre_flag == 1:
                        logger.debug('cml - korea drama %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_show_genre(item, daum_tv_info, ktv_show_target_path)
                    elif ktv_show_target_path is not None and ktv_show_genre_flag == 0:
                        logger.debug('cml - korea drama %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_show(item, daum_tv_info, ktv_show_target_path)
                    else:
                        LogicNormal.move_except(item, error_target_path)
                else:
                    LogicNormal.move_except(item, error_target_path)
            #Movie
            else:
                from framework.common.daum import MovieSearch
                logger.debug('cml - movie %s', item['name'])
                for keywords in rules:
                    gregx = re.compile(keywords, re.I)
                    if (gregx.search(item['name'])) is not None:
                        item['uhd'] += 1

                if 'year' in item['guessit']:
                    year = item['guessit']['year']
                    (item['is_include_kor'], daum_movie_info) = MovieSearch.search_movie(item['search_name'], item['guessit']['year'])
                    if daum_movie_info and daum_movie_info[0]['score'] >= 100:
                        LogicNormal.set_movie(item, daum_movie_info[0])
                        LogicNormal.move_movie(item, daum_movie_info[0], movie_target_path)
                    else:
                        LogicNormal.move_except(item, error_target_path)
                else:
                    LogicNormal.move_except(item, error_target_path)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def set_ktv(data, ktv):
        try:
            data['ktv'] = ktv
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', ktv['title']).replace('  ', ' '))
            folder_rule = ModelSetting.get_setting_value('folder_rule')
            tmp = folder_rule.replace('%TITLE%', ktv['title']).replace('%GENRE%', ktv['genre'])
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
                if not 'country' in movie['more']:
                    if movie['country'] is not None:
                        movie['more']['country'] = movie['country']
                folder_rule = ModelSetting.get_setting_value('folder_rule')
                tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title'])
                #tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title']).replace('%COUNTRY%', movie['more']['country']).replace('%GENRE%', movie['more']['genre']).replace('%DATE%', movie['more']['date']).replace('%RATE%', movie['more']['rate']).replace('%DURING%', movie['more']['during'])
                tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
                data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv_drama(data, info, base_path):
        uhd_ktv_drama_base_path = ModelSetting.get('uhd_ktv_drama_base_path')
        try:
            logger.debug('=== title %s', data['dest_folder_name'])
            title = data['dest_folder_name']
            fullPath = data['fullPath']
            if data['uhd'] > 0:
                LogicNormal.move_ktv_drama_uhd(data, info, uhd_ktv_drama_base_path)
                return
            dest_folder_path = os.path.join(base_path.strip(), title.encode('utf-8'))
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(fullPath.encode('utf-8'), dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv_drama_uhd(data, info, base_path):
        try:
            logger.debug('=== title %s', data['dest_folder_name'])
            title = data['dest_folder_name']
            fullPath = data['fullPath']

            dest_folder_path = os.path.join(base_path.strip(), title.encode('utf-8'))
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(fullPath.encode('utf-8'), dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv_show(data, info, base_path):
        try:
            logger.debug('=== title %s', data['dest_folder_name'])
            title = data['dest_folder_name']
            fullPath = data['fullPath']

            dest_folder_path = os.path.join(base_path.strip(), title.encode('utf-8'))
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(fullPath.encode('utf-8'), dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv_show_genre(data, info, base_path):
        try:
            set_genre = []
            logger.debug('=== title %s', data['dest_folder_name'])
            if 'genre' in info:
                set_genre = info['genre']
            else:
                set_genre = u'기타'
            title = data['dest_folder_name']
            fullPath = data['fullPath']

            dest_folder_path = os.path.join(base_path.strip(), set_genre.encode('utf-8'), title.encode('utf-8'))
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(fullPath.encode('utf-8'), dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_except(data, base_path):
        try:
            dest_folder_path = os.path.join(base_path.strip())
            logger.debug('me - move exception %s' , data['search_name'])
            if not os.path.isdir(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(data['fullPath'], dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'불일치', False)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_movie(data, info, base_path):
        if ModelSetting.get('movie_sort').strip():
            sort = ast.literal_eval(ModelSetting.get('movie_sort'))
        else:
            sort = None
        if ModelSetting.get('movie_country_option').strip():
            movie_country_option = ast.literal_eval(ModelSetting.get('movie_country_option'))
        else:
            movie_country_option = None
        if ModelSetting.get('movie_year_option').strip():
            movie_year_option = ast.literal_eval(ModelSetting.get('movie_year_option'))
        else:
            movie_year_option = None
        if ModelSetting.get('movie_rate_option').strip():
            movie_rate_option = ast.literal_eval(ModelSetting.get('movie_rate_option'))
        else:
            movie_rate_option = None
        uhd_base_path = ModelSetting.get('uhd_base_path')
        ani_base_path = ModelSetting.get('ani_base_path')
        uhd_flag = ModelSetting.get_bool('uhd_flag')
        arg1 = ""
        arg2 = ""
        arg3 = ""
        try:
            for k, v in sort.items():
                logger.debug('mm - k:%s, v:%s', k, v)
                if k == u'국가':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_country(info, movie_country_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_country(info, movie_country_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_country(info, movie_country_option)
                if k == u'연도':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_year(info, movie_year_option)
                if k == u'등급':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_rate(info, movie_rate_option)

            check_ani = LogicNormal.check_ani(info)
            if data['uhd'] > 0 and uhd_flag == 1:
                LogicNormal.move_movie_uhd(data, info, uhd_base_path)
                return
            elif check_ani >= 1:
                set_cat = u'애니메이션'
                target = u'극장판'
                dest_folder_path = os.path.join(ani_base_path, data['dest_folder_name'])
            else:
                if arg1 and arg2 and arg3:
                    logger.debug('mm - arg1+2+3')
                    dest_folder_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), arg3.encode('utf-8'), data['dest_folder_name'])
                    logger.debug('mm - dest_folder_path:%s', dest_folder_path)
                elif arg1 and arg2:
                    logger.debug('mm - arg1+2')
                    dest_folder_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), data['dest_folder_name'])
                    logger.debug('mm - dest_folder_path:%s', dest_folder_path)
                elif arg1:
                    logger.debug('mm - arg1')
                    dest_folder_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), data['dest_folder_name'])
                    logger.debug('mm - dest_folder_path:%s', dest_folder_path)
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(data['fullPath'], dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_movie_uhd(data, info, base_path):
        eng_title_flag = ModelSetting.get_bool('eng_title_flag')
        try:
            if eng_title_flag == 1:
                dest_folder_name = '%s' % (re.sub('[\\/:*?"<>|]', '', info['more']['eng_title']).replace('  ', ' '))
                dest_folder_path = os.path.join(base_path.strip(), dest_folder_name)
            else:
                dest_folder_path = os.path.join(base_path.strip(), data['dest_folder_name'])

            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)
            fileCheck = os.path.join(dest_folder_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(data['fullPath'], dest_folder_path)
                LogicNormal.db_save(data, dest_folder_path, u'일치', True)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_country(info, option):
        try:
            country = []
            set_country = ""
            if 'more' in info:
                if 'country' in info['more']:
                    country = info['more']['country']
            else:
                if 'country' in info:
                    country = info['country']

            if country is not None:
                for keywords, values in option.items():
                    encKeywords = keywords.encode('utf-8')
                    gregx = re.compile(encKeywords, re.I)
                    if (gregx.search(country)) is not None:
                        encValues = values.encode('utf-8')
                        set_country = encValues
                        logger.debug('mpc - country:%s, encValues:%s', set_country, encValues)
                        break
                    else:
                        set_country = u'외국'
                return set_country
            else:
                return None
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_year(info, option):
        try:
            set_year = ""
            temp = None
            if info['year'] is not None:
                for keywords, values in sorted(option.items()):
                    #encKeywords = keywords.encode('utf-8')
                    encValues = values.encode('utf-8')
                    if int(info['year']) <= keywords:
                        set_year = encValues
                        logger.debug('mpy break - year:%s, encValues:%s', set_year, encValues)
                        break
                return set_year
            else:
                return None
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_rate(info, option):
        try:
            rate = []
            set_rate = ""
            if 'more' in info:
                if 'rate' in info['more']:
                    rate = info['more']['rate']

            if rate is not None:
                for keywords, values in option.items():
                    encKeywords = keywords.encode('utf-8')
                    gregx = re.compile(encKeywords, re.I)
                    if (gregx.search(rate)) is not None:
                        encValues = values.encode('utf-8')
                        set_rate = encValues
                        logger.debug('mpr - rate:%s, encValues:%s', set_rate, encValues)
                        break
                    else:
                        set_rate = u'기타'
                return set_rate
            else:
                return None
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def check_ani(info):
        ani_flag = ModelSetting.get_bool('ani_flag')
        try:
            condition = 0
            if ani_flag == 1:
                if 'more' in info:
                    if 'info' in info['more']:
                        keywords = ''.join(info['more']['info'])
                        for words in keywords.split('|'):
                            if u' 애니메이션 외' in words:
                                condition += 1
                            else:
                                condition -= 0

                if condition == 0:
                    if 'genre' in info:
                        if u'애니메이션' in info['genre']:
                            condition += 1
                        else:
                            condition -= 0
            return condition
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def empty_folder_remove(base_path):
        base_path = unicode(base_path)
        if not os.path.isdir(base_path):
           return

        files = os.listdir(base_path)
        if len(files):
            for f in files:
                fullPath = os.path.join(path, f)
                if os.path.isdir(fullPath):
                    LogicNormal.empty_folder_remove(fullPath)
        # if folder empty, delete it
        files = os.listdir(path)
        if len(files) == 0:
            logger.debug('Removing empty folder: %s', path)
            os.rmdir(path)

    @staticmethod
    def db_save(data, dest, match_type, is_moved):
        try:
            entity = {}
            entity['name'] = data['search_name']
            entity['fileName'] = data['name']
            entity['dirName'] = data['fullPath']
            entity['targetPath'] = dest
            entity['match_type'] = match_type
            if is_moved:
                entity['is_moved'] = 1
            else:
                entity['is_moved'] = 0
            ModelItem.save_as_dict(entity)
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
