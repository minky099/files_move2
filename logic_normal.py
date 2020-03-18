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
                fileList = LogicNormal.make_list(source_base_path)
                LogicNormal.check_move_list(fileList, ktv_base_path, movie_base_path, error_path)
                time.sleep(int(interval))

            except Exception as e:
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())

            if ModelSetting.get_bool('emptyFolderDelete'):
                fileList.reverse()
                for item in fileList:
                    logger.debug( "dir_path : " + item['fullPath'])
                    if source_base_path != item['fullPath'] and len(os.listdir(item['fullPath'])) == 0:
                        os.rmdir(unicode(item['fullPath']))

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def make_list(source_base_path):
        try:
            fileList = []
            for path in source_base_path:
                logger.debug('path:%s', path)
                lists = os.listdir(path)
                for f in lists:
                    try:
                        item = {}
                        item['path'] = path
                        item['name'] = f
                        item['fullPath'] = os.path.join(path, f)
                        if os.path.isfile(item['fullPath']):
                            pass
                        item['guessit'] = guessit(f)
                        item['ext'] = os.path.splitext(f)[1].lower()
                        item['search_name'] = None
                        match = re.compile('^(?P<name>.*?)[\\s\\.\\[\\_\\(]\\d{4}').match(item['name'])
                        if match:
                            item['search_name'] = match.group('name').replace('.', ' ').strip()
                            item['search_name'] = re.sub('\\[(.*?)\\]', '', item['search_name'])
                        fileList.append(item)
                    except Exception as e:
                        logger.error('Exxception:%s', e)
                        logger.error(traceback.format_exc())

            return fileList
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def check_move_list(list, ktv_target_path, movie_target_path, error_target_path):
        try:
            for item in list:
                if 'episode' in item['guessit']:
                    #TV
                    logger.debug('cml - drama')
                    daum_tv_info = daum_tv.Logic.get_daum_tv_info(item['search_name'])
                    if daum_tv_info:
                        logger.debug('cml - daum_tv_info[countries]: %s', daum_tv_info['countries'])
                        for country in daum_tv_info['countries']:
                            item['country'] = daum_tv_info.countries.add(country.strip())

                        logger.debug('cml - item[country]: %s', item['country'])
                        if 'country' in item['country'] == u'한국':
                            LogicNormal.move_ktv(item, daum_tv_info, ktv_target_path)
                        else:
                            LogicNormal.move_except(item, error_target_path)
                    else:
                        LogicNormal.move_execpt(item, error_target_path)

                else:
                    #Movie
                    logger.debug('cml - movie')
                    if 'year' in item['guessit']:
                        daum_movie_info = daum_tv.MovieSearch.search_movie(item['search_name'], item['guessit']['year'])
                        if daum_movie_info:
                            LogicNormal.set_movie(item, daum_moive_info)
                            LogicNormal.move_movie(item, daum_movie_info, movie_target_path)
                        else:
                            LogicNormal.move_except(item, error_target_path)
                    else:
                        LogicNormal.move_except(item, error_target_path)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def set_movie(data, movie):
        try:
            data['movie'] = movie
            data['dest_folder_name'] = '%s' % (re.sub('[\\/:*?"<>|]', '', movie['title']).replace('  ', ' '))
            if 'more' in movie:
                Logic = Logic
                import logic
                folder_rule = Logic.get_setting_value('folder_rule')
                tmp = folder_rule.replace('%TITLE%', movie['title']).replace('%YEAR%', movie['year']).replace('%ENG_TITLE%', movie['more']['eng_title']).replace('%COUNTRY%', movie['more']['country']).replace('%GENRE%', movie['more']['genre']).replace('%DATE%', movie['more']['date']).replace('%RATE%', movie['more']['rate']).replace('%DURING%', movie['more']['during'])
                tmp = re.sub('[\\/:*?"<>|]', '', tmp).replace('  ', ' ').replace('[]', '')
                data['dest_folder_name'] = tmp
        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_ktv(data, info, base_path):
        try:
            logger.debug('=== title %s', info.title)
            dest_folder_path = os.path.join(base_path, u'드라마', u'한국', unicode(info.title))
            if not os.path.isdir(dest_folder_path):
                os.makedirs(dest_folder_path)
            shutil.move(data['fullPath'], dest_folder_path)
            LogicNormal.db_save(info, dest_folder_path)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_except(data, base_path):
        try:
            dest_folder_path = os.path.join(base_path, data['search_name'])
            if not os.path.isdir(dest_folder_path):
                os.makedirs(dest_folder_path)
            shutil.move(data['fullPath'], dest_folder_path)
            LogicNormal.db_save(info, dest_folder_path)

        except Exception as e:
            logger.error('Exxception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def move_movie(data, info, base_path):
        try:
            logger.debug('mm - info[more][country]: %s', info['more']['country'])
            if info['more']['country'] == u'한국':
                set_country = u'한국'
            elif info['more']['country'] == u'중국':
                set_country = u'증국'
            elif info['more']['country'] == u'홍콩':
                set_country = u'증국'
            elif info['more']['country'] == u'대만':
                set_country = u'증국'
            elif info['more']['country'] == u'일본':
                set_country = u'일본'
            else:
                set_country = u'외국'

            if info['year'] < 1990:
                set_year = u'1900s'
            elif info['year'] >= 1990 and info['year'] < 2000:
                set_year = u'1990s'
            elif info['year'] >= 2000 and info['year'] < 2010:
                set_year = u'2000s'
            elif info['year'] >= 2010 and info['year'] <= 2012:
                set_year = u'~2012'
            elif info['year'] == 2013:
                set_year = u'2013'
            elif info['year'] == 2014:
                set_year = u'2014'
            elif info['year'] == 2015:
                set_year = u'2015'
            elif info['year'] == 2016:
                set_year = u'2016'
            elif info['year'] == 2017:
                set_year = u'2017'
            elif info['year'] == 2018:
                set_year = u'2018'
            elif info['year'] == 2019:
                set_year = u'2019'
            elif info['year'] == 2020:
                set_year = u'2020'

            dest_folder_path = os.path.join(base_path, u'영화', set_country, set_year, data['dest_folder_name'])
            if not os.path.isdir(dest_folder_path):
                os.makedirs(dest_folder_path)
            shutil.move(data['fullPath'], dest_folder_path)
            LogicNormal.db_save(info, dest_folder_path)

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

