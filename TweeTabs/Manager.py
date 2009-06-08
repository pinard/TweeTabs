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
import gobject, os, random, simplejson, sys
import twyt.twitter, twyt.data

import Common, Strip

class Error(Common.Error):
    pass

twitter = twyt.twitter.Twitter()

# Set these from your ~/.tweetabs/defaults.py file, rather than here.
user = None
password = None
blanking_delay = 4

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

class Manager:
    auth_limit = 50
    ip_limit = 50
    blanker_active = False
    within_delay_loop = False

    def __init__(self):
        twitter.set_user_agent("TweeTabs")
        twitter.set_auth(user, password)
        self.error_list = []
        self.delayed_iterators = []
        self.create_deltas()

    def start(self):
        pass

    def delay(self, iterator):
        self.delayed_iterators.append(iterator)
        if not self.within_delay_loop and len(self.delayed_iterators) == 1:
            gobject.timeout_add(self.suggested_delta(), self.delay_loop)

    def delay_loop(self):
        self.within_delay_loop = True
        pick = random.randint(0, len(self.delayed_iterators) - 1) 
        iterator = self.delayed_iterators.pop(pick)
        try:
            postponer = iterator()
        except StopIteration:
            pass
        else:
            if postponer is not None:
                postponer(iterator)
        self.auth_limit -= 1
        if self.delayed_iterators:
            gobject.timeout_add(self.suggested_delta(), self.delay_loop)
        self.within_delay_loop = False

    def create_deltas(self):
        a = 0
        b = 1
        deltas = []
        while len(deltas) < 11 or b < 30 * 60:
            a, b = b, a + b
            deltas.append(a)
        self.deltas = deltas[-11:]

    def suggested_delta(self):
        limit = max(0, min(100, self.auth_limit))
        return 1000 * self.deltas[(100 - limit) // 10]

    def message(self, message=None):
        if message:
            Common.gui.twitter_message_widget.set_markup(
                    '<span size="small">' + Common.escape(message) + '</span>')
        else:
            Common.gui.twitter_message_widget.set_label('')
        Common.gui.refresh()

    def error(self, message):
        self.error_list.append(message)
        if not self.blanker_active:
            gobject.timeout_add(int(1000 * blanking_delay),
                                self.error_displayer)
            self.blanker_active = True
            self.error_displayer()

    def error_displayer(self):
        if self.error_list:
            Common.gui.twitter_error_widget.set_markup(
                    '<span size="small" weight="bold" foreground="red">'
                    + Common.escape(self.error_list.pop(0)) + '</span>')
            Common.gui.refresh()
            return True
        Common.gui.twitter_error_widget.set_label('')
        Common.gui.refresh()
        self.blanker_active = False
        return False

    ## Twitter services.

    @twytcall("getting Auth limit")
    def get_auth_limit(self):
        response = twyt.data.RateLimit(twitter.account_rate_limit_status(True))
        self.auth_limit = response['remaining_hits']
        self.display_limits()

    @twytcall("getting IP limit")
    def get_ip_limit(self):
        response = twyt.data.RateLimit(twitter.account_rate_limit_status(False))
        self.ip_limit = response['remaining_hits']
        self.display_limits()

    @twytcall("fetching followers")
    def fetch_followers(self, tab):
        tab.preset_strips = set(map(
            Strip.User,
            simplejson.loads(twitter.social_graph_followers_ids())))
        tab.refresh()

    @twytcall("fetching following")
    def fetch_following(self, tab):
        tab.preset_strips = set(map(
            Strip.User,
            simplejson.loads(twitter.social_graph_friends_ids())))
        tab.refresh()

    @twytcall("getting user info")
    def get_user_info(self, id):
        return twitter.user_show(id)

    @twytcall("loading direct timeline")
    def load_direct_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twitter.direct_messages())))
        tab.refresh()

    @twytcall("loading direct sent timeline")
    def load_direct_sent_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet, twyt.data.StatusList(twitter.direct_sent())))
        tab.refresh()

    @twytcall("loading friends timeline")
    def load_friends_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twitter.status_friends_timeline())))
        tab.refresh()

    @twytcall("loading public timeline")
    def load_public_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twitter.status_public_timeline())))
        tab.refresh()

    @twytcall("loading replies timeline")
    def load_replies_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twitter.status_replies())))
        tab.refresh()

    @twytcall("loading user timeline")
    def load_user_timeline(self, tab):
        tab.preset_strips |= set(map(
            Strip.Tweet,
            twyt.data.StatusList(twitter.status_user_timeline())))
        tab.refresh()

    @twytcall("sending tweet")
    def send_tweet(self, message):
        twitter.status_update(message)

    ## Services.

    def display_limits(self):
        Common.gui.twitter_limits_widget.set_markup(
                '<span  size="small" foreground="gray50">%s/%s</span>'
                 % (self.auth_limit, self.ip_limit))
        Common.gui.refresh()

if Common.threaded:

    import Queue, threading

    class Threaded_Manager(threading.Thread, Manager):
        quit_flag = False

        def __init__(self):
            threading.Thread.__init__(self, name="Twitter manager")
            self.queue = Queue.Queue()
            Manager.__init__(self)

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
