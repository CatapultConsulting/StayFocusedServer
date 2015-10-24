#!/usr/bin/env python3.4
# -*- coding: UTF-8 -*-

import os
import sys

import uuid

import random
import hashlib
import datetime

import pytz
import pytz.reference

import re

import json
import pprint

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
import tornado.process
import tornado.log
import tornado.gen

import motor
import bson
import pymongo

import urllib.parse as urlparse

from tornado.options import options
from tornado.options import define

_ = lambda s: s

##################################################
## Options

def config_callback(path):
    options.parse_config_file(path, final=False)

define('config', type=str, help='Path to config file', callback=config_callback, group='Config file')

define('debug', default=False, help='Debug', type=bool, group='Application')

define('cookie_secret', default=hashlib.sha256(str(random.random()).encode('ascii')).hexdigest(), type=str, group='Cookies')
define('cookie_domain', type=str, group='Cookies')

define('listen_port', default=8000, help='Listen Port', type=int, group='HTTP Server')
define('listen_host', default='localhost', help='Listen Host', type=str, group='HTTP Server')

define('mongodb_uri', default='mongodb://localhost:27017/stayfocused', type=str, group='MongoDB')

define('page_title_prefix', default='Stay Focused Server', type=str, group='Page Information')
define('page_project_url', default='https://github.com/CatapultConsulting/StayFocusedServer', type=str, group='Page Information')
define('page_copyright', default='2015 Catapult Consulting, LLC.', type=str, group='Page Information')

##################################################
## BaseHandler

class BaseHandler(tornado.web.RequestHandler):
    def initialize(self, **kwargs):
        super(BaseHandler, self).initialize(**kwargs)

        self.motor_client = self.settings['motor_client']
        self.motor_db = self.motor_client.get_default_database()

        self.oid = bson.ObjectId()

        self.start = datetime.datetime.now(pytz.UTC)
        self.kwargs = kwargs

    @tornado.gen.coroutine
    def prepare(self):
        tornado.log.gen_log.debug(pprint.pformat({
            'path_args': self.path_args,
            'path_kwargs': self.path_kwargs,
            'kwargs': self.kwargs
        }))

    def get_template_namespace(self):
        namespace = super(BaseHandler, self).get_template_namespace()
        namespace.update({
            'page_copyright': self.settings.get('page_copyright'),
            'page_project_url': self.settings.get('page_project_url'),
            'page_title_prefix': self.settings.get('page_title_prefix'),
            'page_title': '',
        })

        return namespace

##################################################
## PageErrorHandler

class PageErrorHandler(BaseHandler):
    def get(self, *args, **kwargs):
        self.send_error(self.kwargs['error'])

    def post(self, *args, **kwargs):
        self.send_error(self.kwargs['error'])

##################################################
## StubHandler

class StubHandler(BaseHandler):
    def check_xsrf_cookie(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
        self.write(dict(self.request.headers))

    def head(self, *args, **kwargs):
        self.write('')

    def post(self, *args, **kwargs):
        print(self.request.body);
        self.write(self.request.body)

    def patch(self, *args, **kwargs):
        self.write('')

    def delete(self, *args, **kwargs):
        self.write('')

    def options(self, *args, **kwargs):
        self.write('')

##################################################
## Server

def main():

    tornado.options.parse_command_line()

    ##################################################
    ## Server

    code_path = os.path.dirname(__file__)
    static_path = os.path.join(code_path, 'static')
    template_path = os.path.join(code_path, 'templates')
    media_path = os.path.join(code_path, 'media')
    support_path = os.path.join(code_path, 'support')

    handlers = [
        ## Static File Serving
        tornado.web.url(r'/static/(css/.*)', tornado.web.StaticFileHandler, {'path': static_path}),
        tornado.web.url(r'/static/(ico/.*)', tornado.web.StaticFileHandler, {'path': static_path}),
        tornado.web.url(r'/static/(img/.*)', tornado.web.StaticFileHandler, {'path': static_path}),
        tornado.web.url(r'/static/(js/.*)', tornado.web.StaticFileHandler, {'path': static_path}),
        ## Processed Media File Serving
        tornado.web.url(r'/media/(.*)', tornado.web.StaticFileHandler, {'path': media_path}),
        ## API Endpoints
        tornado.web.url('/api/v1/upload/(?P<upload_id>.*)/(?P<device_id>.*)/(?P<project_id>.*)/(?P<timestamp>.*)/(?P<hash>.*)/(?P<image_count>.*)/(?P<upload_id>.*)/$', StubHandler),
        ## Misc
        tornado.web.url(r'/__stub__/$', StubHandler),
    ]

    motor_client = motor.MotorClient(options.mongodb_uri, tz_aware=True, read_preference=pymongo.read_preferences.ReadPreference.NEAREST)

    settings = dict(
        login_url = '/login',
        logout_url = '/logout',
        register_url = '/register',
        static_path = static_path,
        template_path = template_path,
        support_path = support_path,
        xsrf_cookies = True,
        motor_client = motor_client,
        **options.as_dict()
    )

    tornado.log.gen_log.debug(pprint.pformat(settings))

    ##################################################
    ## Application

    application = tornado.web.Application(handlers=handlers, **settings)

    http_server = tornado.httpserver.HTTPServer(application, xheaders=True)

    http_server.listen(options.listen_port, address=options.listen_host)

    ioloop = tornado.ioloop.IOLoop.instance()

    try:
        ioloop_status = ioloop.start()
    except KeyboardInterrupt:
        ioloop_status = ioloop.stop()

    return ioloop_status

##################################################
## Application

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        pass

