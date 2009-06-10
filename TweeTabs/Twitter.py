#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 2009 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>, 2009.

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.  */

"""\
A Twitter reader and personal manager - Twitter API management.
"""

__metaclass__ = type
import simplejson
import twyt.twitter, twyt.data

import Common, Scheduler, Strip

class Error(Common.Error):
    pass

twytter = twyt.twitter.Twitter()

# Set these from your ~/.tweetabs/defaults.py file, rather than here.
user = None
password = None

class twytcall:

    def __init__(this, message):
        this.message = message

    def __call__(this, func):

        def decorated(self, *args, **kws):
            self.message(this.message + '…')
            try:
                return func(self, *args, **kws)
            except twyt.twitter.TwitterException, exception:
                diagnostic = str(exception) + ', ' + this.message
                self.error(diagnostic)
                raise Error(diagnostic)
            finally:
                self.message('')

        return decorated

class Twitter:
    auth_limit = 50
    ip_limit = 50

    def __init__(self):
        twytter.set_user_agent("TweeTabs")
        twytter.set_auth(user, password)
        self.error_list = []

    def start(self):
        pass
    
    def message(self, message=None):
        if message:
            Common.gui.twitter_message_widget.set_markup(
                    '<span size="small">' + Common.escape(message) + '</span>')
        else:
            Common.gui.twitter_message_widget.set_label('')
        Common.gui.refresh()

    def error(self, diagnostic):
        self.error_list.append(diagnostic)
        if len(self.error_list) == 1:
            Scheduler.Thread(self.error_thread())

    def error_thread(self):
        while self.error_list:
            diagnostic = self.error_list[0]
            Common.gui.twitter_error_widget.set_markup(
                    '<span size="small" weight="bold" foreground="red">'
                    + Common.escape(diagnostic) + '</span>')
            yield Common.gui.blanking_delay
            Common.gui.twitter_error_widget.set_label('')
            yield 0.2
            self.error_list.pop(0)

    ## Twitter services.

    @twytcall("getting Auth limit")
    def get_auth_limit(self):
        response = twyt.data.RateLimit(twytter.account_rate_limit_status(True))
        self.auth_limit = response['remaining_hits']
        self.display_limits()

    @twytcall("getting IP limit")
    def get_ip_limit(self):
        response = twyt.data.RateLimit(twytter.account_rate_limit_status(False))
        self.ip_limit = response['remaining_hits']
        self.display_limits()

    @twytcall("fetching followers")
    def fetch_followers(self, tab):
        tab.preset_strips = set(map(
            Strip.User,
            simplejson.loads(twytter.social_graph_followers_ids())))
        tab.refresh()

    @twytcall("fetching following")
    def fetch_following(self, tab):
        tab.preset_strips = set(map(
            Strip.User,
            simplejson.loads(twytter.social_graph_friends_ids())))
        tab.refresh()

    @twytcall("getting user info")
    def get_user_info(self, id):
        return twytter.user_show(id)

    @twytcall("loading direct timeline")
    def load_direct_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twytter.direct_messages())))
        tab.refresh()

    @twytcall("loading direct sent timeline")
    def load_direct_sent_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet, twyt.data.StatusList(twytter.direct_sent())))
        tab.refresh()

    @twytcall("loading friends timeline")
    def load_friends_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twytter.status_friends_timeline())))
        tab.refresh()

    @twytcall("loading public timeline")
    def load_public_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twytter.status_public_timeline())))
        tab.refresh()

    @twytcall("loading replies timeline")
    def load_replies_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twytter.status_replies())))
        tab.refresh()

    @twytcall("loading user timeline")
    def load_user_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twytter.status_user_timeline())))
        tab.refresh()

    @twytcall("sending tweet")
    def send_tweet(self, message):
        twytter.status_update(message)

    ## Services.

    def display_limits(self):
        Common.gui.twitter_limits_widget.set_markup(
                '<span  size="small" foreground="gray50">%s/%s</span>'
                 % (self.auth_limit, self.ip_limit))
        Common.gui.refresh()

if Common.threaded:

    import Queue, threading

    class Threaded_Twitter(threading.Thread, Twitter):
        quit_flag = False

        def __init__(self):
            threading.Thread.__init__(self, name="Twitter manager")
            self.queue = Queue.Queue()
            Twitter.__init__(self)

        def run(self):
            while not self.quit_flag:
                try:
                    func, args, kws = self.queue.get(timeout=delay)
                    func(*args, **kws)
                    self.queue.task_done()
                except Queue.Empty:
                    pass

        def enqueue(self, func, *args, **kws):
            self.queue.put((func, args, kws))

        def quit(self):
            self.quit_flag = True
