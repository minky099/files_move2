# -*- coding: UTF-8 -*-
# SJVA, Plex SJ Daum Agent, shell 공용
import os
import sys
import re
import traceback
import logging
import urllib
import requests
import lxml.html
#import json
#import unicodedata

#DAUM_MOVIE_DETAIL = "http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s"

# SJVA
from .plugin import logger, package_name

is_plex = False
#headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
#headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1'}
#headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2919.83 Safari/537.36'}
#my_cookies = {
#'TIARA':'GFjs3T_NUldfaNq1Wv57AFCm3q6aZ-bKo6ws7e7ijH3Rm5iton5NA9abyBqMlgLp9CgfDfk442XCFKrU8g6p8Qu-n3ShXmtp',
#'UUID': 'ZlDYYJ7b5BHpG2rVZnKk2uSJP6Fuze5wwl.JcQ-vduc0',
#'RUID': 'b7WDhgbQP9P3cpRcszB_x54dgOVZ3Jt8Y68wbhrUDL90',
#'TUID': '5xycgjuHcIcJ_190605142016060',
#'XUID': 'CV22zN3aTua8yJZHOgAaD5m9kKkzCf9jhm4neTfBxWCcWIaLJDLw3I-HStRjOQ-qfd_bPJVulwQrg5xqd7UoJA00'
#}

####################################################
def get_json(url):
    try:
        return requests.get(url).json()
    except Exception as e:
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

def get_html(url):
    #headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2919.83 Safari/537.36'}
    #cookies = {'TIARA': 'GFjs3T_NUldfaNq1Wv57AFCm3q6aZ-bKo6ws7e7ijH3Rm5iton5NA9abyBqMlgLp9CgfDfk442XCFKrU8g6p8Qu-n3ShXmtp', 'UUID': 'ZlDYYJ7b5BHpG2rVZnKk2uSJP6Fuze5wwl.JcQ-vduc0', 'RUID': 'b7WDhgbQP9P3cpRcszB_x54dgOVZ3Jt8Y68wbhrUDL90', 'TUID': '5xycgjuHcIcJ_190605142016060', 'XUID': 'CV22zN3aTua8yJZHOgAaD5m9kKkzCf9jhm4neTfBxWCcWIaLJDLw3I-HStRjOQ-qfd_bPJVulwQrg5xqd7UoJA00'}
    try:
        with requests.Session() as s:
            s.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2919.83 Safari/537.36'})
            #s.cookies.set(**my_cookies)
            s.cookies.set('TIARA', 'UGW1xtn4YKAmqYXfc_FW.vIqTlqAQ1DPsaWrixwHrVf6BsR..W3Yfm2_fJN7Tr97RepQmpIDDP255dKZNCtRRwYq_LnCkF3G')
            s.cookies.set('UUID', 'I41mWZivIqIc2.gQmLm2E_TLoaDsof1zYyFdoLTC_hU0')
            s.cookies.set('RUID', 'VPav-azRrrcw.q9f5ohG2DG36dxksb7ez6PZomVVMFU0')
            s.cookies.set('TUID', 'r5mrQF4b5UFo_200215225759853')
            s.cookies.set('XUID', 'AGRX5MKvvwl2h.K.-jQIXcI5dRCc-XSeSmWxEdggU9X_ft3HJWDn2Ji3BHnFVlrK2-l_fUikj6LNMcjXt6kFDw00')
            #return lxml.html.document_fromstring(requests.get(url, headers=headers, cookies=cookies).content)
            res = s.get(url).content
            ret = lxml.html.document_fromstring(res)
        return ret
    except Exception as e:
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())
####################################################

class MovieSearch(object):
    @staticmethod
    def search_movie(movie_name, movie_year):
        try:
            movie_year = '%s' % movie_year
            movie_list = []

            #8년 전쟁 이란 vs 이라크
            split_index = -1
            is_include_kor = False
            for index, c in enumerate(movie_name):
                if ord(u'가') <= ord(c) <= ord(u'힣'):
                    is_include_kor = True
                    split_index = -1
                elif ord('a') <= ord(c.lower()) <= ord('z'):
                    is_include_eng = True
                    if split_index == -1:
                        split_index = index
                elif ord('0') <= ord(c.lower()) <= ord('9') or ord(' '):
                    pass
                else:
                    split_index = -1

            if is_include_kor and split_index != -1:
                kor = movie_name[:split_index].strip()
                eng = movie_name[split_index:].strip()
            else:
                kor = None
                eng = None
            logger.debug('SEARCH_MOVIE : [%s] [%s] [%s] [%s]' % (movie_name, is_include_kor, kor, eng))

            movie_list = MovieSearch.search_movie_web(movie_list, movie_name, movie_year)
            if movie_list and movie_list[0]['score'] == 100:
                logger.debug('SEARCH_MOVIE STEP 1 : %s' % movie_list)
                return is_include_kor, movie_list

            if kor is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, kor, movie_year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 2 : %s' % movie_list)
                    return is_include_kor, movie_list

            if eng is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, eng, movie_year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 3 : %s' % movie_list)
                    return is_include_kor, movie_list

            #검찰측의 죄인 検察側の罪人. Kensatsu gawa no zainin. 2018.1080p.KOR.FHDRip.H264.AAC-RTM
            # 영어로 끝나지전은 한글
            # 그 한글중 한글로 시작하지 않는곳까지
            if kor is not None:
                tmps = kor.split(' ')
                index = -1
                for i in range(len(tmps)):
                    if ord(u'가') <= ord(tmps[i][0]) <= ord(u'힣') or ord('0') <= ord(tmps[i][0]) <= ord('9'):
                        pass
                    else:
                        index = i
                        break
                if index != -1:
                    movie_list = MovieSearch.search_movie_web(movie_list, ' '.join(tmps[:index]), movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 4 : %s' % movie_list)
                        return is_include_kor, movie_list

            if is_plex == False:
                # 95점이면 맞다고 하자. 한글로 보내야하기때문에 검색된 이름을..
                if movie_list and movie_list[0]['score'] == 95:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie_list[0]['title'], movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 5 : %s' % movie_list)
                        return is_include_kor, movie_list

            # IMDB
            if is_include_kor == False:
                movie = MovieSearch.search_imdb(movie_name.lower(), movie_year)
                if movie is not None:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie['title'], movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP IMDB : %s' % movie_list)
                        return is_include_kor, movie_list

            logger.debug('SEARCH_MOVIE STEP LAST : %s' % movie_list)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return is_include_kor, movie_list

    @staticmethod
    def movie_append(movie_list, data):
        try:
            flag_exist = False
            for tmp in movie_list:
                if tmp['id'] == data['id']:
                    flag_exist = True
                    tmp['score'] = data['score']
                    tmp['title'] = data['title']
                    if 'country' in data:
                        tmp['country'] = data['country']
                    break
            if not flag_exist:
                movie_list.append(data)
                #logger.debug('ma -  %s', data)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def get_movie_info_from_home(url):
        try:
            html = get_html(url)
            movie = None
            try:
                movie = html.get_element_by_id('movieEColl')
            except Exception as e:
                #logger.error('Exception:%s', e)
                #logger.error('SEARCH_MOVIE NOT MOVIEECOLL')
                pass
            if movie is None:
                logger.debug('gmifh - movie is none')
                return None

            title_tag = movie.get_element_by_id('movieTitle')
            a_tag = title_tag.find('a')
            href = a_tag.attrib['href']
            title = a_tag.find('b').text_content()

            # 2019-08-09
            tmp = title_tag.text_content()
            #tmp_year = movie_year
            tmp_year = ''
            match = re.compile(ur'(?P<year>\d{4})\s제작').search(tmp)

            more = {}
            if match:
                tmp_year = match.group('year')
                more['eng_title'] = tmp.replace(title, '').replace(tmp_year, '').replace(u'제작', '').replace(u',', '').strip()

            country_tag = movie.xpath('//div[3]/div/div[1]/div[2]/dl[1]/dd[2]')
            country = ''
            if country_tag:
                country = country_tag[0].text_content().split('|')[0].strip()
                logger.debug(country)
            more['poster'] = movie.xpath('//*[@id="nmovie_img_0"]/a/img')[0].attrib['src']
            more['title'] = movie.xpath('//*[@id="movieTitle"]/span')[0].text_content()
            tmp = movie.xpath('//*[@id="movieEColl"]/div[3]/div/div[1]/div[2]/dl')
            more['info'] = []
            #for t in tmp:
            #    more['info'].append(t.text_content().strip())
            #more['info'].append(tmp[0].text_content().strip())
            more['info'].append(country_tag[0].text_content().strip())

            #2019-09-07
            logger.debug(more['info'][0])
            tmp = more['info'][0].split('|')
            if len(tmp) == 5:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = tmp[2].replace(u'개봉', '').strip()
                more['rate'] = tmp[3].strip()
                more['during'] = tmp[4].strip()
            elif len(tmp) == 4:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = ''
                more['rate'] = tmp[2].strip()
                more['during'] = tmp[3].strip()
            elif len(tmp) == 3:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = ''
                more['rate'] = ''
                more['during'] = tmp[2].strip()
            daum_id = href.split('=')[1]
            return {'movie':movie, 'title':title, 'daum_id':daum_id, 'year':tmp_year, 'country':country, 'more':more}

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def search_movie_web(movie_list, movie_name, movie_year):
        condition = 0
        try:
            #movie_list = []
            url = 'https://suggest-bar.daum.net/suggest?id=movie&cate=movie&multiple=1&mod=json&code=utf_in_out&q=%s' % (urllib.quote(movie_name.encode('utf8')))
            data = get_json(url)

            for index, item in enumerate(data['items']['movie']):
                tmps = item.split('|')
                score = 85 - (index*5)
                if tmps[0].find(movie_name) != -1 and tmps[-2] == movie_year:
                    score = 95
                elif tmps[-2] == movie_year:
                    score = score + 5
                if score < 10:
                    score = 10
                MovieSearch.movie_append(movie_list, {'id':tmps[1], 'title':tmps[0], 'year':tmps[-2], 'score':score})
                logger.debug('smw - id[%s]%s', index, tmps[1])
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        try:
            for idx in range(len(movie_list)):
                logger.debug('smw - score:%s, myear:%s, [%s]year:%s', movie_list[idx]['score'], movie_year, idx, movie_list[idx]['year'])
                if movie_list[idx]['score'] >= 85 and abs(movie_year - int(movie_list[idx]['year'])) <= 1:
                    logger.debug('smw - id(%s):%s', movie_list[idx]['score'], movie_list[idx]['id'])
                    more_url = 'http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s' % movie_list[idx]['id']
                    meta_data = get_json(more_url)
                    info = meta_data['data']
                    if movie_year == int(info['prodYear']):
                        movie_list[idx]['score'] = 100
                    elif abs(movie_year - int(info['prodYear'])) <= 1:
                        movie_list[idx]['score'] = 95

                    if int(movie_list[idx]['year']) == 0:
                       movie_list[idx]['year'] = unicode(info['prodYear'])
                    movie_list[idx]['title'] = info['titleKo']
                    logger.debug('smw - eng title:%s', info['titleEn'])
                    #movie_list[0].update({'more':{'eng_title':[]}})
                    movie_list[idx].update({'more':{'eng_title':"", 'genre':[]}})
                    movie_list[idx]['more']['eng_title'] = info['titleEn']
                    for item in info['countries']:
                      movie_list[idx]['country'] = item['countryKo']
                      break;
                    #movie_list[0]['country'] = info['countries']['countryKo']
                    #movie_list[0].update({'more':{'genre':[]}})
                    for item in info['genres']:
                        movie_list[idx]['more']['genre'].append(item['genreName'])
                        logger.debug(item['genreName'])
                        condition += 1
        except Exception as e:
            pass
            #logger.error('Exception:%s', e)
            #logger.error(traceback.format_exc())

        try:
            url = 'https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=%s%s' % ('%EC%98%81%ED%99%94+', urllib.quote(movie_name.encode('utf8')))
            ret = MovieSearch.get_movie_info_from_home(url)
            if ret is not None:
                # 부제목때문에 제목은 체크 하지 않는다.
                # 홈에 검색한게 년도도 같다면 score : 100을 주고 다른것은 검색하지 않는다.
                if ret['year'] == movie_year:
                    score = 100
                    need_another_search = False
                else:
                    score = 90
                    need_another_search = True
                MovieSearch.movie_append(movie_list, {'id':ret['daum_id'], 'title':ret['title'], 'year':ret['year'], 'score':score, 'country':ret['country'], 'more':ret['more']})

                logger.debug('need_another_search : %s' % need_another_search)

                movie = ret['movie']

                if need_another_search:
                    # 동명영화
                    tmp = movie.find('div[@class="coll_etc"]')
                    logger.debug('coll_etc : %s' % tmp)
                    if tmp is not None:
                        first_url = None
                        tag_list = tmp.findall('.//a')
                        for tag in tag_list:
                            match = re.compile(r'(.*?)\((.*?)\)').search(tag.text_content())
                            if match:
                                daum_id = tag.attrib['href'].split('||')[1]
                                score = 80
                                if match.group(1) == movie_name and match.group(2) == movie_year:
                                    first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                                elif match.group(2) == movie_year and first_url is not None:
                                    first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                                MovieSearch.movie_append(movie_list, {'id':daum_id, 'title':match.group(1), 'year':match.group(2), 'score':score})
                                #results.Append(MetadataSearchResult(id=daum_id, name=match.group(1), year=match.group(2), score=score, lang=lang))
                        logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            #logger.debug('RRRRRRRRRRRRRRRRRRRRRR')
                            new_ret = MovieSearch.get_movie_info_from_home(first_url)
                            MovieSearch.movie_append(movie_list, {'id':new_ret['daum_id'], 'title':new_ret['title'], 'year':new_ret['year'], 'score':100, 'country':new_ret['country'], 'more':new_ret['more']})

                    #시리즈
                    tmp = movie.find('.//ul[@class="list_thumb list_few"]')
                    if tmp is None:
                        tmp = movie.find('.//ul[@class="list_thumb list_more"]')

                    logger.debug('SERIES:%s' % tmp)
                    if tmp is not None:
                        tag_list = tmp.findall('.//div[@class="wrap_cont"]')
                        first_url = None
                        score = 80
                        for tag in tag_list:
                            a_tag = tag.find('a')
                            daum_id = a_tag.attrib['href'].split('||')[1]
                            daum_name = a_tag.text_content()
                            span_tag = tag.find('span')
                            year = span_tag.text_content()
                            logger.debug('daum_id:%s %s %s' % (daum_id, year, daum_name))
                            if daum_name == movie_name and year == movie_year:
                                first_url = 'https://search.daum.net/search?%s' % a_tag.attrib['href']
                            elif year == movie_year and first_url is not None:
                                first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                            MovieSearch.movie_append(movie_list, {'id':daum_id, 'title':daum_name, 'year':year, 'score':score})
                            logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            #logger.debug('RRRRRRRRRRRRRRRRRRRRRR')
                            new_ret = MovieSearch.get_movie_info_from_home(first_url)
                            MovieSearch.movie_append(movie_list, {'id':new_ret['daum_id'], 'title':new_ret['title'], 'year':new_ret['year'], 'score':100, 'country':new_ret['country'], 'more':new_ret['more']})

                    if condition == 0:
                       if movie_list[0]['score'] >= 95:
                            logger.debug('smw another - id:%s', movie_list[0]['id'])
                            more_url = 'http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s' % movie_list[0]['id']
                            meta_data = get_json(more_url)
                            info = meta_data['data']
                            for item in info['genres']:
                                movie_list[0]['more']['genre'].append(item['genreName'])
                                logger.debug(item['genreName'])
                                condition += 1
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        movie_list = list(reversed(sorted(movie_list, key=lambda k:k['score'])))
        return movie_list

    @staticmethod
    def search_imdb(title, year):
        try:
            year = int(year)
            title = title.replace(' ', '_')
            url = 'https://v2.sg.media-imdb.com/suggestion/%s/%s.json' % (title[0], title)
            tmp = get_json(url)
            if 'd' in tmp and tmp['d'][0]['y'] == year:
                return {'id':tmp['d'][0]['id'], 'title':tmp['d'][0]['l'], 'year':year, 'score':100}
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
