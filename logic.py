# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import time
import threading
import subprocess

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
		'ktv_show_base_path' : '',
		'movie_base_path' : '',
		'error_path' : '',
		'uhd_base_path' : '',
		'ani_base_path' : '',
		'movie_sort' : '',
		'movie_country_option' : '',
		'movie_year_option' : '',
		'movie_rate_option' : '',
		'ani_flag' : '',
		'uhd_flag' : '',
		'ktv_show_genre_flag' : '',
		'uhd_ktv_drama_flag' : '',
		'eng_title_flag' : '',
        'schedulerInterval' : '60',
        'interval' : '3',
        'emptyFolderDelete' : 'False',
        'auto_start' : 'False',
        'folder_rule': '%TITLE%'
    }

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
            job = Job(package_name, package_name, ModelSetting.get('schedulerInterval'), Logic.scheduler_function, u"파일정리", False)
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

    @staticmethod
    def fileList(req):

        try:
            ret = { }
            page = 1
            page_size = int(db.session.query(ModelSetting).filter_by(key = 'web_page_size').first().value)
            job_id = ''
            search = ''
            if 'page' in req.form:
               page = int(req.form['page'])
            if 'search_word' in req.form:
               search = req.form['search_word']
            query = db.session.query(ModelItem)
            if search != '':
                query = query.filter(ModelItem.filename.like('%' + search + '%'))
            option = req.form['option']
            if option == 'all':
                pass
            order = 'desc'
            if order == 'desc':
               query = query.order_by(desc(ModelItem.id))
            else:
               query = query.order_by(ModelItem.id)
            count = query.count()
            query = query.limit(page_size).offset((page - 1) * page_size)
            logger.debug('ModelFileprocessMovieItem count:%s', count)
            lists = query.all()
            ret['list'] = [ item.as_dict() for item in lists ]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

