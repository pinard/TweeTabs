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
A Twitter reader and personal manager - Strip structures.
"""

__metaclass__ = type
import re, sys, time

import pygtk
pygtk.require('2.0')
import gtk

import Common

class Strip:

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return str(self.key)

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(self.key)

    def new_widget(self):
        hbox = gtk.HBox()
        button = gtk.Button('☺')
        hbox.pack_start(button, False, False, Common.gui.spacing)
        label = gtk.Label(str(self))
        label.set_line_wrap(True)
        hbox.pack_start(label, False, False)
        hbox.show_all()
        return hbox

class Tweet(Strip):

    def __init__(self, status):
        self.status = status
        Strip.__init__(self, status.id)

    def new_widget(self):

        def tweet():
            hbox = gtk.HBox()
            text = gtk.Label()
            text.set_line_wrap(True)
            text.set_selectable(True)
            text.set_markup(
                    '<span weight="bold" foreground="brown">'
                    + Common.escape(self.status.user.screen_name + ':')
                    + '</span> ' + markup_with_links(self.status.text))
            hbox.pack_start(text, False, False)
            return hbox

        def stats():
            hbox = gtk.HBox()
            left = gtk.Label()
            left.set_markup(
                    '<span size="small" foreground="gray50">'
                     + Common.escape(transform_stamp(self.status.created_at))
                     + '</span>')
            hbox.pack_start(left, False, False)
            right = gtk.Label()
            right.set_markup(
                    '<span size="small" style="italic" foreground="gray50">'
                    + Common.escape(self.status.source) + ',</span>'
                    + ' <span size="small" foreground="gray50">'
                    + Common.escape(str(self.status.id)) + '</span>')
            hbox.pack_end(right, False, False)
            return hbox

        def image():
            vbox = gtk.VBox()
            button = gtk.Button('☺')
            vbox.pack_start(button, False, False)
            return vbox

        vbox = gtk.VBox()
        vbox.pack_start(tweet(), False, False)
        vbox.pack_start(stats(), False, False)

        hbox = gtk.HBox()
        hbox.pack_start(vbox, False, False)
        hbox.pack_end(image(), False, False)
        hbox.show_all()
        return hbox

## Services.

def markup_with_links(text):
    pattern = ('https?://[-_a-zA-Z0-9%./?&=#]+'
               '|@[^ :,]+'
               '|\\#[a-zA-Z][a-zA-Z0-9]+'
               '|RT\\b')
    marked = ''
    position = 0
    for match in re.finditer(pattern, text):
        start = match.start()
        if text[start] == '@':
            span = '<span foreground="brown">'
        elif text[start] == '#':
            span = '<span foreground="darkmagenta">'
        elif text[start] == 'R':
            span = '<span weight="bold" style="italic">'
        else: # http:// or https://
            span = '<span underline="single" foreground="darkgreen">'
        marked += (Common.escape(text[position:start])
                   + span + Common.escape(match.group()) + '</span>')
        position = match.end()
    marked += Common.escape(text[position:])
    return marked

monthname_to_month = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

def transform_stamp(stamp):
    try:
        # Code from Andrew Price, in twyt.  It does not work just here! ☹
        utc = time.mktime(time.strptime('%s UTC' % stamp,
                                        '%a %b %d %H:%M:%S +0000 %Y %Z'))
        stamp = time.strftime('%Y-%m-%d %H:%M', time.localtime(utc))
    except ValueError:
        # Format is like "Sat May 30 20:25:43 +0000 2009".
        dayname, monthname, day, clock, zone, year = stamp.split()
        stamp = '%s-%.2d-%s %s GMT' % (
                year, monthname_to_month[monthname], day, clock[:5])
    return stamp
