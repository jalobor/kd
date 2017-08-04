#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Module: LibraryExporter
# Created on: 13.01.2017

import os
from shutil import rmtree
from utils import noop
try:
   import cPickle as pickle
except:
   import pickle

class Library:
    """Exports Netflix shows & movies to a local library folder"""

    series_label = 'shows'
    """str: Label to identify shows"""

    movies_label = 'movies'
    """str: Label to identify movies"""

    db_filename = 'lib.ndb'
    """str: (File)Name of the store for the database dump that contains all shows/movies added to the library"""

    def __init__ (self, root_folder, library_settings, log_fn=noop):
        """Takes the instances & configuration options needed to drive the plugin

        Parameters
        ----------
        root_folder : :obj:`str`
            Cookie location

        library_settings : :obj:`str`
            User data cache location

        library_db_path : :obj:`str`
            User data cache location

        log_fn : :obj:`fn`
             optional log function
        """
        self.base_data_path = root_folder
        self.enable_custom_library_folder = library_settings['enablelibraryfolder']
        self.custom_library_folder = library_settings['customlibraryfolder']
        self.db_filepath = os.path.join(self.base_data_path, self.db_filename)
        self.log = log_fn

        # check for local library folder & set up the paths
        lib_path = self.base_data_path if self.enable_custom_library_folder != 'true' else self.custom_library_folder
        self.movie_path = os.path.join(lib_path, self.movies_label)
        self.tvshow_path = os.path.join(lib_path, self.series_label)

        # check if we need to setup the base folder structure & do so if needed
        self.setup_local_netflix_library(source={
            self.movies_label: self.movie_path,
            self.series_label: self.tvshow_path
        })

        # load the local db
        self.db = self._load_local_db(filename=self.db_filepath)

    def setup_local_netflix_library (self, source):
        """Sets up the basic directories

        Parameters
        ----------
        source : :obj:`dict` of :obj:`str`
            Dicitionary with directories to be created
        """
        for label in source:
            if not os.path.exists(source[label]):
                os.makedirs(source[label])

    def write_strm_file(self, path, url):
        """Writes the stream file that Kodi can use to integrate it into the DB

        Parameters
        ----------
        path : :obj:`str`
            Filepath of the file to be created

        url : :obj:`str`
            Stream url
        """
        with open(path, 'w+') as f:
            f.write(url)
            f.close()

    def _load_local_db (self, filename):
        """Loads the local db file and parses it, creates one if not existent

        Parameters
        ----------
        filename : :obj:`str`
            Filepath of db file

        Returns
        -------
        :obj:`dict`
            Parsed contents of the db file
        """
        # if the db doesn't exist, create it
        if not os.path.isfile(filename):
            data = {self.movies_label: {}, self.series_label: {}}
            self.log('Setup local library DB')
            self._update_local_db(filename=filename, db=data)
            return data

        with open(filename) as f:
            data = pickle.load(f)
            if data:
                return data
            else:
                return {}

    def _update_local_db (self, filename, db):
        """Updates the local db file with new data

        Parameters
        ----------
        filename : :obj:`str`
            Filepath of db file

        db : :obj:`dict`
            Database contents

        Returns
        -------
        bool
            Update has been successfully executed
        """
        if not os.path.isdir(os.path.dirname(filename)):
            return False
        with open(filename, 'w') as f:
            f.truncate()
            pickle.dump(db, f)
        return True

    def movie_exists (self, title, year):
        """Checks if a movie is already present in the local DB

        Parameters
        ----------
        title : :obj:`str`
            Title of the movie

        year : :obj:`int`
            Release year of the movie

        Returns
        -------
        bool
            Movie exists in DB
        """
        movie_meta = '%s (%d)' % (title, year)
        return movie_meta in self.db[self.movies_label]

    def show_exists (self, title):
        """Checks if a show is present in the local DB

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        Returns
        -------
        bool
            Show exists in DB
        """
        show_meta = '%s' % (title)
        return show_meta in self.db[self.series_label]

    def season_exists (self, title, season):
        """Checks if a season is present in the local DB

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        season : :obj:`int`
            Season sequence number

        Returns
        -------
        bool
            Season of show exists in DB
        """
        if self.show_exists(title) == False:
            return False
        show_entry = self.db[self.series_label][title]
        return season in show_entry['seasons']

    def episode_exists (self, title, season, episode):
        """Checks if an episode if a show is present in the local DB

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        season : :obj:`int`
            Season sequence number

        episode : :obj:`int`
            Episode sequence number

        Returns
        -------
        bool
            Episode of show exists in DB
        """
        if self.show_exists(title) == False:
            return False
        show_entry = self.db[self.series_label][title]
        episode_entry = 'S%02dE%02d' % (season, episode)
        return episode_entry in show_entry['episodes']

    def add_movie (self, title, alt_title, year, video_id, build_url):
        """Adds a movie to the local db, generates & persists the strm file

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        alt_title : :obj:`str`
            Alternative title given by the user

        year : :obj:`int`
            Release year of the show

        video_id : :obj:`str`
            ID of the video to be played

        build_url : :obj:`fn`
            Function to generate the stream url
        """

        movie_meta = '%s (%d)' % (title, year)
        folder = alt_title
        dirname = os.path.join(self.movie_path, folder)
        filename = os.path.join(dirname, movie_meta + '.strm')
        if os.path.exists(filename):
            return
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        if self.movie_exists(title=title, year=year) == False:
            self.db[self.movies_label][movie_meta] = {'alt_title': alt_title}
            self._update_local_db(filename=self.db_filepath, db=self.db)
        self.write_strm_file(path=filename, url=build_url({'action': 'play_video', 'video_id': video_id}))

    def add_show (self, title, alt_title, episodes, build_url):
        """Adds a show to the local db, generates & persists the strm files

        Note: Can also used to store complete seasons or single episodes, it all depends on
        what is present in the episodes dictionary

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        alt_title : :obj:`str`
            Alternative title given by the user

        episodes : :obj:`dict` of :obj:`dict`
            Episodes that need to be added

        build_url : :obj:`fn`
            Function to generate the stream url
        """
        show_meta = '%s' % (title)
        folder = alt_title
        show_dir = os.path.join(self.tvshow_path, folder)
        if not os.path.exists(show_dir):
            os.makedirs(show_dir)
        if self.show_exists(title) == False:
            self.db[self.series_label][show_meta] = {'seasons': [], 'episodes': [], 'alt_title': alt_title}
        for episode in episodes:
            self._add_episode(show_dir=show_dir, title=title, season=episode['season'], episode=episode['episode'], video_id=episode['id'], build_url=build_url)
        self._update_local_db(filename=self.db_filepath, db=self.db)
        return show_dir

    def _add_episode (self, title, show_dir, season, episode, video_id, build_url):
        """Adds a single episode to the local DB, generates & persists the strm file

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        show_dir : :obj:`str`
            Directory that holds the stream files for that show

        season : :obj:`int`
            Season sequence number

        episode : :obj:`int`
            Episode sequence number

        video_id : :obj:`str`
            ID of the video to be played

        build_url : :obj:`fn`
            Function to generate the stream url
        """
        season = int(season)
        episode = int(episode)

        # add season
        if self.season_exists(title=title, season=season) == False:
            self.db[self.series_label][title]['seasons'].append(season)

        # add episode
        episode_meta = 'S%02dE%02d' % (season, episode)
        if self.episode_exists(title=title, season=season, episode=episode) == False:
            self.db[self.series_label][title]['episodes'].append(episode_meta)

        # create strm file
        filename = episode_meta + '.strm'
        filepath = os.path.join(show_dir, filename)
        if os.path.exists(filepath):
            return
        self.write_strm_file(path=filepath, url=build_url({'action': 'play_video', 'video_id': video_id}))

    def remove_movie (self, title, year):
        """Removes the DB entry & the strm file for the movie given

        Parameters
        ----------
        title : :obj:`str`
            Title of the movie

        year : :obj:`int`
            Release year of the movie

        Returns
        -------
        bool
            Delete successfull
        """
        movie_meta = '%s (%d)' % (title, year)
        folder = self.db[self.movies_label][movie_meta]['alt_title']
        del self.db[self.movies_label][movie_meta]
        self._update_local_db(filename=self.db_filepath, db=self.db)
        dirname = os.path.join(self.movie_path, folder)
        if os.path.exists(dirname):
            rmtree(dirname)
            return True
        return False

    def remove_show (self, title):
        """Removes the DB entry & the strm files for the show given

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        Returns
        -------
        bool
            Delete successfull
        """
        folder = self.db[self.series_label][title]['alt_title']
        del self.db[self.series_label][title]
        self._update_local_db(filename=self.db_filepath, db=self.db)
        show_dir = os.path.join(self.tvshow_path, folder)
        if os.path.exists(show_dir):
            rmtree(show_dir)
            return True
        return False

    def remove_season (self, title, season):
        """Removes the DB entry & the strm files for a season of a show given

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        season : :obj:`int`
            Season sequence number

        Returns
        -------
        bool
            Delete successfull
        """
        season = int(season)
        season_list = []
        episodes_list = []
        show_meta = '%s' % (title)
        for season_entry in self.db[self.series_label][show_meta]['seasons']:
            if season_entry != season:
                season_list.append(season_entry)
        self.db[self.series_label][show_meta]['seasons'] = season_list
        show_dir = os.path.join(self.tvshow_path, self.db[self.series_label][show_meta]['alt_title'])
        if os.path.exists(show_dir):
            show_files = [f for f in os.listdir(show_dir) if os.path.isfile(os.path.join(show_dir, f))]
            for filename in show_files:
                if 'S%02dE' % (season) in filename:
                    os.remove(os.path.join(show_dir, filename))
                else:
                    episodes_list.append(filename.replace('.strm', ''))
            self.db[self.series_label][show_meta]['episodes'] = episodes_list
        self._update_local_db(filename=self.db_filepath, db=self.db)
        return True

    def remove_episode (self, title, season, episode):
        """Removes the DB entry & the strm files for an episode of a show given

        Parameters
        ----------
        title : :obj:`str`
            Title of the show

        season : :obj:`int`
            Season sequence number

        episode : :obj:`int`
            Episode sequence number

        Returns
        -------
        bool
            Delete successfull
        """
        episodes_list = []
        show_meta = '%s' % (title)
        episode_meta = 'S%02dE%02d' % (season, episode)
        show_dir = os.path.join(self.tvshow_path, self.db[self.series_label][show_meta]['alt_title'])
        if os.path.exists(os.path.join(show_dir, episode_meta + '.strm')):
            os.remove(os.path.join(show_dir, episode_meta + '.strm'))
        for episode_entry in self.db[self.series_label][show_meta]['episodes']:
            if episode_meta != episode_entry:
                episodes_list.append(episode_entry)
        self.db[self.series_label][show_meta]['episodes'] = episodes_list
        self._update_local_db(filename=self.db_filepath, db=self.db)
        return True
