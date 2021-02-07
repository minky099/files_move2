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
from framework import py_urllib
import rclone
#import platform
#import daum_tv

# third-party
from sqlalchemy import desc
from sqlalchemy import or_, and_, func, not_
from guessit import guessit

# sjva 공용
from framework import app, db, scheduler, path_app_root, celery, py_unicode
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
                for source_path in source_base_path:
                    LogicNormal.make_list(source_path, ktv_drama_base_path, ktv_show_base_path, movie_base_path, error_path)
                    if ModelSetting.get_bool('extraFilesMove'):
                        LogicNormal.extra_files_move(source_path)
                    if ModelSetting.get_bool('extraMove'):
                        LogicNormal.extra_move(source_path)
                    if ModelSetting.get_bool('emptyFolderDelete'):
                        LogicNormal.empty_folder_remove(source_path)

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
            if 'Trailer' in f:
                return None
            item['fullPath'] = os.path.join(path, f)
            temp = re.sub('(s|S)+\d\d', '', f)
            #logger.debug('il1 - %s : %s', item['name'], temp)
            temp = re.sub('-\d?\d', '', temp)
            #logger.debug('il2 - %s : %s', item['name'], temp)
            temp = re.sub('\d?\d회 ?합?본?', '', temp)
            #temp = re.sub('\d\d-\d\d회 합본', '', temp)
            #logger.debug('il3 - %s : %s', item['name'], temp)
            logger.debug('il4 - temp:%s', temp)
            #item['guessit'] = guessit(temp, options={'date-day-first': True})
            item['guessit'] = guessit(temp)
            item['ext'] = os.path.splitext(f)[1].lower()
            item['search_name'] = None
            item['uhd'] = 0
            item['hd'] = 0
            item['fhd'] = 0
            #match = re.compile('^(?P<name>.*?)[\\s\\.\\[\\_\\(]\\d{4}').match(item['name'])
            match = re.compile('^(?P<name>.*?)[\\s\\.\\[\\_\\(]\\d{4}').match(temp)
            if match:
                item['search_name'] = match.group('name').replace('.', ' ').strip()
                item['search_name'] = re.sub('\\[(.*?)\\]', '', item['search_name'])
            else:
                return None
            if LogicNormal.isHangul(item['search_name']) > 0:
                str = py_unicode(item['search_name'])
                item['search_name'] = str
            logger.debug('il5 - search_name:%s', item['search_name'])
            return item
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def empty_folder_remove(base_path):
        try:
            logger.debug('efr - base_path:%s', base_path)
            for root, dirs, files in os.walk(base_path, topdown=False):
                for name in dirs:
                    try:
                        if len(os.listdir(os.path.join(root, name))) == 0:
                            logger.debug('efr - Deleting:%s', os.path.join(root, name))
                            try:
                                os.rmdir(os.path.join(root, name))
                            except:
                                logger.debug('efr - FAILED:%s', os.path.join(root, name))
                                pass
                    except:
                        pass
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def extra_files_move(base_path):
        error_path = ModelSetting.get('error_path')
        try:
            logger.debug('efm - path:%s', base_path)
            lists = os.listdir(base_path.strip())
            for f in lists:
                try:
                    if LogicNormal.isHangul(str(f)) > 0:
                        f = f.encode('utf-8')
                    p = os.path.join(base_path.strip(), f)
                    #logger.debug('efm - f:%s p:%s', f, p)
                    #logger.debug('p:%s', p)
                    if os.path.isfile(p):
                        if u'poster.jpg' in f or u'poster.png' in f or u'movie.nfo' in f or u'fanart.jpg' in f or u'fanart.png' in f:
                            extraFilesPath = os.path.split(p)
                            #logger.debug('efm - eFP:%s base:%s', extraFilesPath[0], base_path)
                            (check, dest) = LogicNormal.check_from_db_for_extra_files(extraFilesPath[0])
                            #logger.debug('efm - check:%s dest:%s', check, dest)
                            if check and dest != error_path:
                                shutil.move(p, dest)
                                logger.debug('[extra files move] %s => %s', p, dest)
                    elif os.path.isdir(p):
                        LogicNormal.extra_files_move(p)
                except Exception as e:
                    logger.error('Exxception:%s', e)
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def extra_move(base_path):
        error_path = ModelSetting.get('error_path')
        try:
            logger.debug('em - path:%s', base_path)
            lists = os.listdir(base_path.strip())
            for f in lists:
                try:
                    if LogicNormal.isHangul(str(f)) > 0:
                        f = f.encode('utf-8')
                    p = os.path.join(base_path.strip(), f)
                    #logger.debug('p:%s', p)
                    if os.path.isdir(p):
                        (check, dest) = LogicNormal.check_from_db(p, base_path)
                        if check and dest != error_path:
                            sub_list = os.listdir(p.strip())
                            for sub_f in sub_list:
                                if LogicNormal.isHangul(str(sub_f)) > 0:
                                    sub_f = sub_f.encode('utf-8')
                                sub_p = os.path.join(p.strip(), sub_f)
                                if os.path.isdir(sub_p):
                                    shutil.move(sub_p, dest)
                            logger.debug('[extra move] %s => %s', p, dest)
                        else:
                            LogicNormal.extra_move(p)
                except Exception as e:
                    logger.error('Exxception:%s', e)
                    logger.error(traceback.format_exc())
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def make_list(source_path, ktv_drama_path, ktv_show_path, movie_path, err_path):
        interval = ModelSetting.get('interval')
        try:
            #logger.debug('path:%s', source_path)
            lists = os.listdir(source_path.strip())
            for f in lists:
                try:
                    if LogicNormal.isHangul(str(f)) > 0:
                        f = f.encode('utf-8')
                    #f = str(f).strip()
                    p = os.path.join(source_path.strip(), f)
                    #logger.debug('p:%s', p)
                    if os.path.isdir(p):
                        LogicNormal.make_list(p, ktv_drama_path, ktv_show_path, movie_path, err_path)
                    elif os.path.isfile(p):
                        item = LogicNormal.item_list(source_path, f)
                        if item is not None:
                            item = LogicNormal.check_resolution(item)
                            LogicNormal.check_move_list(item, ktv_drama_path, ktv_show_path, movie_path, err_path)
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
            weight_con = 0
            season_con = re.compile('(s|S)+\d?\d')
            if season_con.search(item['name']):
                weight_con += 1
            episode_con = re.compile('(e|E)+\d?\d?\d')
            if episode_con.search(item['name']):
                weight_con += 1
            logger.debug('cml - weight:%s', weight_con)
            #TV Show
            if 'episode' in item['guessit'] > 0 and item['guessit']['type'] == 'episode' and weight_con > 0:
                from tv import DaumTV
                #from framework.common.daum import DaumTV
                logger.debug('cml - drama %s, %s, %s', item['name'], item['search_name'], item['guessit']['title'])
                tmp_title_0 = item['guessit']['title']
                tmp_title_1 = item['search_name']
                tmp_title_1 = re.sub('(e|E)+\d\d?\d\d?', '', tmp_title_1)
                tmp_title_1 = re.sub('(e|E)+(n|N)+(d|D)', '', tmp_title_1)
                if tmp_title_0.isalpha and LogicNormal.isHangul(tmp_title_0) > 0:
                  #title_tmp = re.sub('[A-Za-z0-9._]', '', tmp_title_0)
                  title_tmp = re.sub(r'\[[^)]*\]', '', tmp_title_0)
                  title_tmp = py_unicode(title_tmp.strip())
                  item['guessit']['title'] = title_tmp
                  logger.debug('cml - title_check:%s', title_tmp)

                daum_tv_info = DaumTV.get_daum_tv_info(item['guessit']['title'])
                if daum_tv_info is not None:
                  LogicNormal.set_ktv(item, daum_tv_info)
                  if item['dest_folder_name'] != item['guessit']['title']:
                    if tmp_title_1.isalpha and LogicNormal.isHangul(tmp_title_1) > 0:
                      #title_tmp = re.sub('[A-Za-z0-9._]', '', tmp_title_0)
                      title_tmp = re.sub(r'\[[^)]*\]', '', tmp_title_1)
                      title_tmp = py_unicode(title_tmp.strip())
                      item['guessit']['title'] = title_tmp
                      logger.debug('cml - title_check:%s', title_tmp)
                      daum_tv_info = DaumTV.get_daum_tv_info(item['guessit']['title'])
                #daum_tv_info = DaumTV.get_daum_tv_info(item['search_name'])
                if daum_tv_info is not None:
                    if daum_tv_info['genre'] == u'드라마':
                        logger.debug('cml - korea drama %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_drama(item, daum_tv_info, ktv_drama_target_path)
                    elif ktv_show_genre_flag == 1:
                        logger.debug('cml - korea show genre %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_show_genre(item, daum_tv_info, ktv_show_target_path)
                    elif ktv_show_target_path is not None and ktv_show_genre_flag == 0:
                        logger.debug('cml - korea show %s', daum_tv_info['genre'])
                        LogicNormal.set_ktv(item, daum_tv_info)
                        LogicNormal.move_ktv_show(item, daum_tv_info, ktv_show_target_path)
                    else:
                        LogicNormal.move_except(item, error_target_path)
                else:
                    LogicNormal.move_except(item, error_target_path)
            #Movie
            else:
                from api_daum_movie import MovieSearch
                #from framework.common.daum import MovieSearch
                logger.debug('cml - movie %s', item['name'])
                if 'year' not in item['guessit']:
                  for cy_name in item['name'].splitlines():
                    try:
                      tmp_year = re.search('\d{4}', cy_name).group(0)
                    except:
                      tmp_year = re.search('\d{4}', cy_name)
                    if int(tmp_year) > 1900:
                      item['guessit']['year'] = tmp_year
                if 'year' in item['guessit']:
                    logger.debug('cml - movie %s year %s', item['name'], item['guessit']['year'])
                    (item['is_include_kor'], daum_movie_info) = MovieSearch.search_movie(item['search_name'], item['guessit']['year'])
                    if (daum_movie_info and daum_movie_info[0]['score'] >= 100):
                        logger.debug('cml - movie score %s', daum_movie_info[0]['score'])
                        #logger.debug('cml - rate : %s', daum_movie_info[0]['more']['rate'])
                        LogicNormal.set_movie(item, daum_movie_info[0])
                        LogicNormal.move_movie(item, daum_movie_info[0], movie_target_path)
                    elif daum_movie_info and daum_movie_info[0]['score'] >= 90:
                        logger.debug('cml - movie score %s', daum_movie_info[0]['score'])
                        if 'more' in daum_movie_info[0]:
                            if'eng_title' in daum_movie_info[0]['more']:
                                logger.debug('cml - movie %s:%s', item['guessit']['title'], daum_movie_info[0]['more']['eng_title'])
                                #if LogicNormal.isHangul(str_cmp_0) > 0:
                                    #korean = re.compile('[\u3130-\u318F\uAC00-\uD7A3]+')
                                str_cmp_0 = re.sub('[^A-Za-z0-9\s]', '', item['guessit']['title'])
                                str_cmp_0 = py_unicode(str_cmp_0.strip())
                                str_cmp_1 = daum_movie_info[0]['more']['eng_title']
                                str_cmp_1 = py_unicode(str_cmp_1)
                                logger.debug('cml - movie cmp %s:%s', str_cmp_0.lower(), str_cmp_1.lower())
                                if str_cmp_0.lower() == str_cmp_1.lower():
                                    logger.debug('cml - movie file name checked!')
                                    LogicNormal.set_movie(item, daum_movie_info[0])
                                    LogicNormal.move_movie(item, daum_movie_info[0], movie_target_path)
                                else:
                                     LogicNormal.move_except(item, error_target_path)
                            else:
                                 LogicNormal.move_except(item, error_target_path)
                        else:
                             LogicNormal.move_except(item, error_target_path)
                    else:
                        LogicNormal.move_except(item, error_target_path)
                else:
                    logger.debug('cml - movie NOT have year!')
                    LogicNormal.move_except(item, error_target_path)
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def set_ktv(data, ktv):
        try:
            data['ktv'] = ktv
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', ktv['title']).replace('  ', ' '))
            #folder_rule = ModelSetting.get_setting_value('folder_rule')
            folder_rule = '%TITLE%'
            tmp = folder_rule.replace('%TITLE%', ktv['title'])
            tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
            data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def set_movie(data, movie):
        tmp = ""
        try:
            data['movie'] = movie
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', movie['title']).replace('  ', ' '))
            folder_rule = ModelSetting.get_setting_value('folder_rule')
            tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year'])
            if 'more' in movie:
                if not 'country' in movie['more']:
                    if movie['country'] is not None:
                        movie['more']['country'] = movie['country']

                if 'eng_title' in movie['more']:
                    tmp = tmp.replace('%ENG_TITLE%', movie['more']['eng_title'])
                if 'country' in movie['more']:
                    tmp = tmp.replace('%COUNTRY%', movie['more']['country'])
                if 'rate' in movie['more']:
                    tmp = tmp.replace('%RATE%', movie['more']['rate'])
                if 'during' in movie['more']:
                    tmp = tmp.replace('%DURING%', movie['more']['during'])
                if 'genre' in movie['more']:
                    genre_list = movie['more']['genre']
                    if isinstance(genre_list, list):
                        genre = genre_list[0]
                    else:
                        genre = genre_list
                    tmp = tmp.replace('%GENRE%', genre)

            tmp = re.sub('%ENG_TITLE%', '', tmp)
            tmp = re.sub('%COUNTRY%', '', tmp)
            tmp = re.sub('%GENRE%', '', tmp)
            tmp = re.sub('%RATE%', '', tmp)
            tmp = re.sub('%DURING%', '', tmp)
            #tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title'])
            #tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title']).replace('%COUNTRY%', movie['more']['country']).replace('%GENRE%', movie['more']['genre']).replace('%DATE%', movie['more']['date']).replace('%RATE%', movie['more']['rate']).replace('%DURING%', movie['more']['during'])
            tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
            data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv_drama(data, info, base_path):
        uhd_ktv_drama_base_path = ModelSetting.get('uhd_ktv_drama_base_path')
        uhd_ktv_drama_flag = ModelSetting.get_bool('uhd_ktv_drama_flag')
        try:
            logger.debug('=== title %s', data['dest_folder_name'])
            title = data['dest_folder_name']
            fullPath = data['fullPath']
            if data['uhd'] > 0 and uhd_ktv_drama_flag == 1:
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
        etc_name = ModelSetting.get('etc_show_genre')
        try:
            set_genre = []
            logger.debug('=== title %s', data['dest_folder_name'])
            if 'genre' in info:
                set_genre = info['genre']
            else:
                if LogicNormal.isHangul(etc_name) > 0:
                    str = py_unicode(etc_name)
                    etc_name = str
                set_genre = etc_name
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
        if ModelSetting.get_setting_value('movie_sort'):
            sort = ast.literal_eval(ModelSetting.get_setting_value('movie_sort').strip())
        else:
            sort = None
        if ModelSetting.get_setting_value('movie_country_option'):
            movie_country_option = ast.literal_eval(ModelSetting.get_setting_value('movie_country_option').strip())
        else:
            movie_country_option = None
        if ModelSetting.get_setting_value('movie_year_option'):
            movie_year_option = ast.literal_eval(ModelSetting.get_setting_value('movie_year_option').strip())
        else:
            movie_year_option = None
        if ModelSetting.get_setting_value('movie_genre_option'):
            movie_genre_option = ast.literal_eval(ModelSetting.get_setting_value('movie_genre_option').strip())
        else:
            movie_genre_option = None
        if ModelSetting.get_setting_value('movie_resolution_option'):
            movie_resolution_option = ast.literal_eval(ModelSetting.get_setting_value('movie_resolution_option').strip())
        else:
            movie_resolution_option = None
        if ModelSetting.get_setting_value('movie_rate_option'):
            movie_rate_option = ast.literal_eval(ModelSetting.get_setting_value('movie_rate_option').strip())
        else:
            movie_rate_option = None
        uhd_base_path = ModelSetting.get('uhd_base_path')
        ani_base_path = ModelSetting.get('ani_base_path')
        uhd_flag = ModelSetting.get_bool('uhd_flag')
        arg1 = ""
        arg2 = ""
        arg3 = ""
        arg4 = ""
        arg5 = ""
        dest_path = ''
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
                    elif v == 3:
                        arg4 = LogicNormal.movie_path_country(info, movie_country_option)
                    elif v == 4:
                        arg5 = LogicNormal.movie_path_country(info, movie_country_option)
                if k == u'연도':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 3:
                        arg4 = LogicNormal.movie_path_year(info, movie_year_option)
                    elif v == 4:
                        arg5 = LogicNormal.movie_path_year(info, movie_year_option)
                if k == u'장르':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_genre(info, movie_genre_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_genre(info, movie_genre_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_genre(info, movie_genre_option)
                    elif v == 3:
                        arg4 = LogicNormal.movie_path_genre(info, movie_genre_option)
                    elif v == 4:
                        arg5 = LogicNormal.movie_path_genre(info, movie_genre_option)
                if k == u'등급':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 3:
                        arg4 = LogicNormal.movie_path_rate(info, movie_rate_option)
                    elif v == 4:
                        arg5 = LogicNormal.movie_path_rate(info, movie_rate_option)
                if k == u'해상도':
                    if v == 0:
                        arg1 = LogicNormal.movie_path_resolution(data, movie_resolution_option)
                    elif v == 1:
                        arg2 = LogicNormal.movie_path_resolution(data, movie_resolution_option)
                    elif v == 2:
                        arg3 = LogicNormal.movie_path_resolution(data, movie_resolution_option)
                    elif v == 3:
                        arg4 = LogicNormal.movie_path_resolution(data, movie_resolution_option)
                    elif v == 4:
                        arg5 = LogicNormal.movie_path_resolution(data, movie_resolution_option)

            check_ani = LogicNormal.check_ani(info)
            if data['uhd'] > 0 and uhd_flag == 1:
                LogicNormal.move_movie_uhd(data, info, uhd_base_path)
                return
            elif check_ani >= 1:
                set_cat = u'애니메이션'
                target = u'극장판'
                dest_path = os.path.join(ani_base_path, data['dest_folder_name'])
            else:
                if arg1 and arg2 and arg3 and arg4 and arg5:
                    dest_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), arg3.encode('utf-8'), arg4.encode('utf-8'), arg5.encode('utf-8'), data['dest_folder_name'])
                elif arg1 and arg2 and arg3 and arg4:
                    dest_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), arg3.encode('utf-8'), arg4.encode('utf-8'), data['dest_folder_name'])
                elif arg1 and arg2 and arg3:
                    dest_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), arg3.encode('utf-8'), data['dest_folder_name'])
                elif arg1 and arg2:
                    dest_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), arg2.encode('utf-8'), data['dest_folder_name'])
                elif arg1:
                    dest_path = os.path.join(base_path.strip(), arg1.encode('utf-8'), data['dest_folder_name'])
            logger.debug('mm - dest_path:%s', dest_path)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            fileCheck = os.path.join(dest_path, data['name'])
            if not os.path.isfile(fileCheck):
                shutil.move(data['fullPath'], dest_path)
                LogicNormal.db_save(data, dest_path, u'일치', True)
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
        etc_name = ModelSetting.get('etc_movie_country')
        try:
            country = ""
            set_country = ""
            if 'more' in info:
                if 'country' in info['more']:
                    country = info['more']['country']
            else:
                if 'country' in info:
                    country = info['country']

            if country is not None:
                country = country.encode('utf-8')
                for keywords, values in option.items():
                    encKeywords = keywords.encode('utf-8')
                    gregx = re.compile(encKeywords, re.I)
                    #logger.debug('mpc - country:%s, values:%s', country, values)
                    if (gregx.search(country)) is not None:
                        encValues = values.encode('utf-8')
                        set_country = encValues
                        logger.debug('mpc search - country:%s, encValues:%s', country, encValues)
                        break
                    else:
                        if LogicNormal.isHangul(etc_name) > 0:
                            str = py_unicode(etc_name)
                            etc_name = str
                        set_country = etc_name
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
            tmp = 0
            if info['year'] is not None:
                keywords = sorted(option.keys())
                for idx in range(len(keywords)):
                    if int(info['year']) == keywords[idx]:
                        logger.debug('mpy perfect match - year:%s, keywords:%s', info['year'], keywords[idx])
                        tmp = keywords[idx]
                        break
                    elif int(info['year']) <= keywords[idx] and idx > 0:
                        if int(info['year']) > keywords[idx-1]:
                            logger.debug('mpy decade match - year:%s, keywords:%s', info['year'], keywords[idx-1])
                            tmp = keywords[idx-1]
                            break
                    elif int(info['year']) >= keywords[idx] and idx < (len(keywords) - 1):
                        if int(info['year']) < keywords[idx+1]:
                            logger.debug('mpy decade base match - year:%s, keywords:%s', info['year'], keywords[idx])
                            tmp = keywords[idx]
                            break
                    else:
                        logger.debug('mpy not match and searching... year:%s, keywords:%s', info['year'], keywords[idx])
                        continue
                values = option.get(tmp)
                encValues = values.encode('utf-8')
                set_year = encValues
                return set_year
            else:
                return None
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_genre(info, option):
        ani_flag = ModelSetting.get_bool('ani_flag')
        etc_name = ModelSetting.get('etc_movie_genre')
        genre_list = []
        try:
            set_genre = None
            if 'more' in info:
                if 'genre' in info['more']:
                    for word in info['more']['genre']:
                        if ani_flag == 1:
                            if u'애니메이션' in word :
                                return None
            #num_genre = len(info['more']['genre'])
            logger.debug('mpg check %s', info['more']['genre'])
            genre_list = info['more']['genre']
            if isinstance(genre_list, list):
                genre = genre_list[0]
            else:
                genre = genre_list
            for keywords, values in option.items():
                genre = genre.encode('utf-8')
                encKeywords = keywords.encode('utf-8')
                gregx = re.compile(encKeywords, re.I)
                if (gregx.search(genre)) is not None:
                    encValues = values.encode('utf-8')
                    set_genre = encValues
                    logger.debug('mpg search - genre:%s, encValues:%s', genre, encValues)
                    break
                else:
                    if LogicNormal.isHangul(etc_name) > 0:
                        str = py_unicode(etc_name)
                        etc_name = str
                    set_genre = etc_name
            logger.debug('mpg ret genre:%s', set_genre)
            return set_genre
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_rate(info, option):
        etc_name = ModelSetting.get('etc_movie_rate')
        try:
            rate = []
            set_rate = ""
            if 'more' in info:
                if 'rate' in info['more']:
                    rate = info['more']['rate']

            if rate is not None:
                rate = rate.encode('utf-8')
                for keywords, values in option.items():
                    encKeywords = keywords.encode('utf-8')
                    gregx = re.compile(encKeywords, re.I)
                    #logger.debug('mpr - rate:%s, values:%s', rate, values)
                    if (gregx.search(rate)) is not None:
                        encValues = values.encode('utf-8')
                        set_rate = encValues
                        logger.debug('mpr search - rate:%s, encValues:%s', rate, encValues)
                        break
                    else:
                        if LogicNormal.isHangul(etc_name) > 0:
                            str = py_unicode(etc_name)
                            etc_name = str
                        set_rate = etc_name
                return set_rate
            else:
                return None
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def movie_path_resolution(data, option):
        uhd_flag = ModelSetting.get_bool('uhd_flag')
        try:
            set_resolution = ""
            values = ""
            encValues = ""
            if uhd_flag == 1:
                if data['uhd'] >= 1:
                    return None
                else:
                    if data['fhd'] >= 1:
                        values = option.get(1080)
                    elif data['hd'] >= 1:
                        values = option.get(720)
                    else:
                        values = u'기타'
            else:
                if data['uhd'] >= 1:
                    values = option.get(2160)
                elif data['fhd'] >= 1:
                    values = option.get(1080)
                elif data['hd'] >= 1:
                    values = option.get(720)
                else:
                    values = u'기타'
            encValues = values.encode('utf-8')
            set_resolution = encValues
            logger.debug('mpre search - encValues:%s', encValues)
            return set_resolution
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
                    if 'genre' in info['more']:
                        logger.debug('ca - genre:%s', info['more']['genre'])
                        if u'애니메이션' in info['more']['genre']:
                            condition += 1
                        for word in info['more']['genre']:
                            if u'애니메이션' in word:
	    	                    condition += 1
                if condition == 0:
                    if 'genre' in info:
                        logger.debug('ca - genre:%s', info['genre'])
                        for word in info['genre']:
                            if u'애니메이션' in word:
                                condition += 1
            logger.debug('check_ani count:%s', condition)
            return condition
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def check_resolution(info):
        rules_uhd = ['4K', '4k', 'UHD', '2160p', '2160P']
        rules_fhd = ['1080p', '1080P', 'fhd', 'FHD']
        rules_hd = ['720p', '720P', 'hd', 'HD']
        fileName = ""
        try:
            #remove hdr word
            #fileName = info['name']
            #fileName = re.sub(r'HDR', '', fileName, flags=re.IGNORECASE)
            if LogicNormal.isHangul(info['name']) > 0:
                str = py_unicode(info['name'])
                fileName = str
            else:
                fileName = info['name']
            fileName = re.sub('[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', ' ', fileName)
            logger.debug('cr - fileName: %s', fileName)
            for keywords in rules_uhd:
                gregx = re.compile(keywords, re.I)
                if (gregx.search(fileName)):
                    info['uhd'] += 1
            for keywords in rules_fhd:
                gregx = re.compile(keywords, re.I)
                if (gregx.search(fileName)):
                    info['fhd'] += 1
            for keywords in rules_hd:
                gregx = re.compile(keywords, re.I)
                if (gregx.search(fileName)):
                    info['hd'] += 1
            logger.debug('cr - uhd:%s, fhd:%s, hd:%s', info['uhd'], info['fhd'], info['hd'])
            if info['uhd'] >= 1 and info['fhd'] >= 1:
                if int(info['uhd']) > int(info['fhd']):
                    info['uhd'] = 1
                    info['fhd'] = 0
                else:
                    info['uhd'] = 0
                    info['fhd'] = 1
            elif info['uhd'] >= 1 and info['hd'] >= 1:
                info['uhd'] = 1
                info['hd'] = 0
            elif info['fhd'] >= 1 and info['hd'] >= 1:
                info['fhd'] = 1
                info['hd'] = 0
            logger.debug('cr - uhd:%s, fhd:%s, hd:%s', info['uhd'], info['fhd'], info['hd'])
            return info
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def db_save(data, dest, match_type, is_moved):
        telegram_flag = ModelSetting.get_bool('telegram')
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
            if telegram_flag == 1:
                text = u'파일정리\n [%s] %s -> %s\n' % (match_type, data['fullPath'], dest)
                #import framework.common.notify as Notify
                #Notify.send_message(text, message_id = 'files_move_result')
                from tool_base import ToolBaseNotify
                ToolBaseNotify.send_message(text, message_id = 'files_move_result')
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
    def check_from_db_for_extra_files(path):
        logger.debug('check_from_db [query]')
        all = ModelItem.get_by_all()
        lists = (reversed(sorted(all)))
        for item in lists:
            #logger.debug(item)
            checkDbDir = os.path.split(item.dirName)
            #targetCheckDbDir = os.path.split(item.targetPath)
            checkPathDir = os.path.split(path)
            if checkDbDir[0] == path:
                subCheckDbDir = os.path.split(checkDbDir[0])
                logger.debug('[cfd] %s : %s', checkPathDir, checkDbDir)
                if subCheckDbDir[1] == checkPathDir[1]:
                    logger.debug('[cfd] %s', path)
                    return (path, item.targetPath)
        return (None, None)

    @staticmethod
    def check_from_db(path, base):
        logger.debug('check_from_db [query]')
        all = ModelItem.get_by_all()
        lists = (reversed(sorted(all)))
        for item in lists:
            #logger.debug(item)
            checkDbDir = os.path.split(item.dirName)
            #targetCheckDbDir = os.path.split(item.targetPath)
            checkPathDir = os.path.split(path)
            if checkDbDir[0] == base:
                continue
            if checkDbDir[0] == path:
                subCheckDbDir = os.path.split(checkDbDir[0])
                logger.debug('[cfd] %s : %s', checkPathDir, checkDbDir)
                if subCheckDbDir[1] == checkPathDir[1]:
                    logger.debug('[cfd] %s', path)
                    return (path, item.targetPath)
        return (None, None)

    @staticmethod
    def isHangul(text):
        if type(text) is not py_unicode:
            encText = text.decode('utf-8')
        else:
            encText = text
        hanCount = len(re.findall(u'[\u3130-\u318F\uAC00-\uD7A3]+', encText))
        return hanCount > 0

    @staticmethod
    def strip_all(x):
      if isinstance(x, str): # if using python2 replace str with basestring to include py_unicode type
        x = x.strip()
      elif isinstance(x, list):
        x = [LogicNormal.strip_all(v) for v in x]
      elif isinstance(x, dict):
        for k, v in x.iteritems():
          x.pop(k)  # also strip keys
          x[ LogicNormal.strip_all(k) ] = LogicNormal.strip_all(v)
      return x
