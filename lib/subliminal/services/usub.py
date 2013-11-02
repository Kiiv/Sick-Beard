# -*- coding: utf-8 -*-
# Copyright 2013 Julien Goret <jgoret@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from . import ServiceBase
from ..exceptions import ServiceError
from ..language import language_set, Language
from ..subtitles import get_subtitle_path, ResultSubtitle
from ..utils import get_keywords, split_keyword
from ..videos import Episode
from bs4 import BeautifulSoup
import logging
import urllib
from sickbeard import db

logger = logging.getLogger("subliminal")

class Usub(ServiceBase):
    server_url = 'http://www.u-sub.net/sous-titres'
    site_url = 'http://www.u-sub.net/'
    api_based = False
    languages = language_set(['fr'])
    videos = [Episode]
    require_video = False
    #required_features = ['permissive']

    def list_checked(self, video, languages):
        return self.query(video.path or video.release, languages, get_keywords(video.guess), series=video.series, season=video.season, episode=video.episode)

    def query(self, filepath, languages, keywords=None, series=None, season=None, episode=None):
        
        ## Check if we really got informations about our episode
        myDB = db.DBConnection()
        myDBcache = db.DBConnection("cache.db")
        sql_show_id = myDB.select("SELECT tvdb_id FROM tv_shows WHERE show_name LIKE ?", ['%'+series+'%'])
        if sql_show_id:
            sql_scene = myDB.select("SELECT scene_season, scene_episode FROM tv_episodes WHERE showid = ? and season = ? and episode = ?", [sql_show_id[0][0],season,episode])
            if sql_scene:
                season=sql_scene[0][0]
                episode= sql_scene[0][1]
            sql_custom_names = myDBcache.select("SELECT show_name FROM scene_exceptions WHERE tvdb_id = ? ORDER BY exception_id asc", [sql_show_id[0][0]])
            if sql_custom_names:
                series=sql_custom_names[0][0]
        if series and season and episode:
            request_series = series.lower().replace(' ', '-')
            if isinstance(request_series, unicode):
                request_series = request_series.encode('utf-8')
            logger.debug(u'Getting subtitles for %s season %d episode %d with language %r' % (series, season, episode, languages))
            r = self.session.get('%s/%s/saison_%s' % (self.server_url, urllib.quote(request_series),season))
            if r.status_code == 404:
                print "Error 404"
                logger.debug(u'Could not find subtitles for %s' % (series))
                return []
        else:
            print "One or more parameter missing"
            raise ServiceError('One or more parameter missing')
        
        ## Check if we didn't got an big and nasty http error
        if r.status_code != 200:
            print u'Request %s returned status code %d' % (r.url, r.status_code)
            logger.error(u'Request %s returned status code %d' % (r.url, r.status_code))
            return []
            
        ## Editing episode informations to be able to use it with our search
        if episode < 10 :
            episode_num='0'+str(episode)
        else :
            episode_num=str(episode)
        season_num = str(season)
        series_name = series.lower().replace(' ', '.')
        possible_episode_naming = [season_num+'x'+episode_num,season_num+episode_num]
        
        
        ## Actually parsing the page for the good subtitles
        soup = BeautifulSoup(r.content, self.required_features)
        subtitles = []
        subtitles_list = soup.find('table', {'id' : 'subtitles_list'})
        link_list = subtitles_list.findAll('a', {'class' : 'dl_link'})
        
        for link in link_list :
            link_url = link.get('href')
            splited_link = link_url.split('/')
            filename = splited_link[len(splited_link)-1]
            for episode_naming in possible_episode_naming :
                if episode_naming in filename :
                    for language in languages:
                        path = get_subtitle_path(filepath, language, self.config.multi)
                        subtitle = ResultSubtitle(path, language, self.__class__.__name__.lower(), '%s' % (link_url))
                        subtitles.append(subtitle)
        return subtitles
    
    def download(self, subtitle):
        ## All downloaded files are zip files
        self.download_zip_file(subtitle.link, subtitle.path)
        return subtitle


Service = Usub
