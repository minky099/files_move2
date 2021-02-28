# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import time
import threading
import subprocess
import requests

# third-party

# sjva 공용
from framework import db, scheduler, path_data, path_app_root, celery
from framework.job import Job
from framework.util import Util
from sqlalchemy import desc, or_, and_, func, not_

# 패키지
from .plugin import logger, package_name
from .model import ModelSetting, ModelItem

from .logic_normal import LogicNormal
#########################################################

class Logic(object):
    db_default = {
        'db_version' : '1',
		'source_base_path' : '',
		'ktv_drama_base_path' : '',
		'uhd_ktv_drama_base_path' : '',
		'ktv_show_base_path' : '',
		'movie_base_path' : '',
		'error_path' : '',
		'uhd_base_path' : '',
		'ani_base_path' : '',
		'movie_sort' : u'{"국가":0, "연도":1}',
		'movie_country_option' : u'{"한국":"한국", "중국":"중국", "홍콩":"중국", "대만":"중국", "일본":"일본"}',
		'movie_year_option' : u'{1900:"1900s", 1990:"1990s", 2000:"2000s", 2012:"~2012", 2013:"2013", 2014:"2014", 2015:"2015", 2016:"2016", 2017:"2017", 2018:"2018", 2019:"2019", 2020:"2020"}',
		'movie_genre_option' : u'{"SF":"SF", "가족":"가족", "공포":"공포", "다큐멘터리":"다큐멘터리", "드라마":"드라마", "로맨스/멜로":"로맨스/멜로", "무협":"무협", "뮤지컬":"뮤지컬", "미스터리":"미스터리", "범죄":"범죄", "서부":"서부", "성인":"성인", "스릴러":"스릴러", "시대극":"시대극", "애니메이션":"애니메이션", "액션":"액션", "어드밴처":"어드밴처", "전쟁":"전쟁", "코미디":"코미디", "판타지":"판타지"}',
		'movie_rate_option' : u'{"12세이상관람가":"12세이상관람가", "15세이상관람가":"15세이상관람가", "전체관람가":"전체관람가", "청소년관람불가":"청소년관람불가"}',
		'movie_resolution_option' : u'{720:"HD", 1080:"FHD", 2160:"UHD"}',
		'etc_movie_country' : u'외국',
		'etc_movie_rate' : u'기타',
		'etc_movie_genre' : u'기타',
		'etc_show_genre' : u'기타',
		'ani_flag' : '',
		'uhd_flag' : '',
		'ktv_show_genre_flag' : '',
		'uhd_ktv_drama_flag' : '',
		'eng_title_flag' : '',
        'schedulerInterval' : '60',
        'interval' : '3',
        'emptyFolderDelete' : 'False',
        'extraMove' : 'False',
        'extraFilesMove' : 'False',
        'auto_start' : 'False',
        'folder_rule': '%TITLE%',
        'telegram' : '',
        'use_smi_to_srt' : ''
    }
    #session = requests.Session()

    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            Logic.db_init()

            if ModelSetting.get_bool('auto_start'):
                Logic.scheduler_start()
            # 편의를 위해 json 파일 생성
            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_start():
        try:
            logger.debug('%s scheduler_start' % package_name)
            #interval = ModelSetting.query.filter_by(key='schedulerInterval').first().value
            interval = ModelSetting.get('schedulerInterval')
            job = Job(package_name, package_name, interval, Logic.scheduler_function, u"파일정리", False)
            scheduler.add_job_instance(job)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def scheduler_stop():
        try:
            logger.debug('%s scheduler_stop' % package_name)
            scheduler.remove_job(package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def scheduler_function():
        try:
            #Test
            ##LogicNormal.scheduler_function()
            source_path=Logic.get_setting_value('source_base_path')
            source_paths=[x.strip()for x in source_path.split(',')]
            if not source_paths:
                return
            if Logic.get_setting_value('use_smi_to_srt')=='True':
                import smi2srt
                if app.config['config']['use_celery']:
                    result=smi2srt.Logic.start_by_path.apply_async((source_path,))
                    result.get()
                else:
                    smi2srt.Logic.start_by_path(work_path=source_path)
            from framework import app
            if app.config['config']['use_celery']:
                result = LogicNormal.scheduler_function.apply_async()
                result.get()
            else:
                LogicNormal.scheduler_function()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def reset_db():
        try:
            db.session.query(ModelItem).delete()
            db.session.commit()
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def one_execute():
        try:
            if scheduler.is_include(package_name):
                if scheduler.is_running(package_name):
                    ret = 'is_running'
                else:
                    scheduler.execute_job(package_name)
                    ret = 'scheduler'
            else:
                def func():
                    time.sleep(2)
                    Logic.scheduler_function()
                threading.Thread(target=func, args=()).start()
                ret = 'thread'

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = 'fail'
        return ret

