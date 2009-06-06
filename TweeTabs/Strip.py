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
import PIL.Image, StringIO, gtk, pango, re, sys, time, urllib

import Common

image_size = 60
image_loader_capacity = 800

class Strip_in_tab:
    selected = False

    def __init__(self, tab, strip):
        self.tab = tab
        self.strip = strip
        self.create_widget()

    def __str__(self):
        return str(self.strip) + ' in ' + str(self.tab)

    def create_widget(self):
        raise NotImplementedError

    def select(self):
        self.selected = True

    def unselect(self):
        self.selected = False

    def toggle_select(self):
        if self.selected:
            self.unselect()
        else:
            self.select()

class Strip:
    in_tab_maker = Strip_in_tab

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return type(self).__name__ + ' ' + str(self.key)

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(self.key)

class Tweet_in_tab(Strip_in_tab):

    def create_widget(self):

        def image():
            vbox = gtk.VBox()
            image = gtk.Image()
            image_loader.load(image, status.user.profile_image_url)
            vbox.pack_start(image, False, False)
            return vbox

        def tweet():
            # Prepare the display.
            textview = gtk.TextView()
            textview.set_editable(False)
            textview.set_cursor_visible(False)
            textview.set_wrap_mode(gtk.WRAP_WORD)
            textbuffer = textview.get_buffer()
            enditer = textbuffer.get_end_iter()
            # Insert the sender.
            textbuffer.insert_with_tags(
                    enditer,
                    status.user.screen_name + ':',
                    textbuffer.create_tag(None,
                                          foreground=Common.gui.user_color,
                                          weight=pango.WEIGHT_BOLD))
            textbuffer.insert(enditer, ' ')
            # Insert the tweet proper.
            text = re.sub('[ \n\r\b\f\0]+', ' ', status.text)
            pattern = ('https?://[-_a-zA-Z0-9%./?&=#]+'
                       '|@[^ :,]+'
                       '|\\#[a-zA-Z][a-zA-Z0-9]+'
                       '|RT\\b')
            position = 0
            for match in re.finditer(pattern, text):
                start = match.start()
                textbuffer.insert(enditer, text[position:start])
                if text[start] == '@':
                    tag = textbuffer.create_tag(
                            None,
                            foreground=Common.gui.user_color)
                elif text[start] == '#':
                    tag = textbuffer.create_tag(
                            None,
                            foreground=Common.gui.tag_color)
                elif text[start] == 'R':
                    tag = textbuffer.create_tag(
                            None,
                            weight=pango.WEIGHT_BOLD,
                            style=pango.STYLE_ITALIC)
                else: # http:// or https://
                    tag = textbuffer.create_tag(
                            None,
                            underline=pango.UNDERLINE_SINGLE,
                            foreground=Common.gui.url_color)
                textbuffer.insert_with_tags(enditer, match.group(), tag)
                position = match.end()
            textbuffer.insert(enditer, text[position:])
            # Insert the date and source
            textbuffer.insert(enditer, '\n')
            textbuffer.insert_with_tags(
                    enditer,
                    transform_stamp(status.created_at),
                    textbuffer.create_tag(None,
                                          #size=pango.SCALE_SMALL,
                                          foreground="gray50"))
            textbuffer.insert(enditer, ', ')
            textbuffer.insert_with_tags(
                    enditer,
                    status.source,
                    textbuffer.create_tag(None,
                                          #size=pango.SCALE_SMALL,
                                          style=pango.STYLE_ITALIC,
                                          foreground="gray50"))
            return textview

        status = self.strip.status

        hbox = gtk.HBox()
        hbox.pack_start(image(), False, False, Common.gui.spacing)
        eventbox = gtk.EventBox()
        eventbox.add(hbox)
        eventbox.connect('button-press-event', self.tweet_clicked)
        self.eventbox_widget = eventbox

        vbox = gtk.VBox()
        vbox.pack_start(eventbox, False, False)

        hbox = gtk.HBox()
        hbox.pack_start(vbox, False, False)
        hbox.pack_start(tweet())
        hbox.show_all()
        self.widget = hbox

    def tweet_clicked(self, widget, event):
        self.toggle_select()

    def select(self):
        if not self.selected:
            Strip_in_tab.select(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color(
                    Common.gui.select_color))

    def unselect(self):
        if self.selected:
            Strip_in_tab.unselect(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color('white'))

class Tweet(Strip):
    in_tab_maker = Tweet_in_tab

    def __init__(self, status):
        self.status = status
        Strip.__init__(self, status.id)

class User_in_tab(Strip_in_tab):

    def create_widget(self):
        hbox = gtk.HBox()
        button = gtk.Button('☺')
        hbox.pack_start(button, False, False, Common.gui.spacing)
        label = gtk.Label(str(self.strip))
        label.set_line_wrap(True)
        hbox.pack_start(label, False, False)
        hbox.show_all()
        self.widget = hbox

class User(Strip):
    in_tab_maker = User_in_tab

## Text services.

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

## Image services.

def pixbuf_from_url(url):
    # Get the image.
    try:
        buffer = urllib.urlopen(url).read()
    except UnicodeError:
        try:
            buffer = urllib.urlopen(url.encode('ISO-8859-1')).read()
        except UnicodeError:
            try:
                buffer = urllib.urlopen(url.encode('UTF-8')).read()
            except UnicodeError:
                return empty_pixbuf
    try:
        im = PIL.Image.open(StringIO.StringIO(buffer))
    except IOError:
        return empty_pixbuf
    if im.mode != 'RGB':
        im = im.convert('RGB')
    # Make it square, keeping the center.
    sx, sy = im.size
    if sx > sy:
        extra = (sx - sy) // 2
        im = im.crop((extra, 0, extra + sy, sy))
    elif sy > sx:
        extra = (sy - sx) // 2
        im = im.crop((0, extra, sx, extra + sx))
    # Resize it.
    im = im.resize((image_size, image_size), PIL.Image.ANTIALIAS)
    return pixbuf_from_pil(im)

def pixbuf_from_pil(im):
    handle = StringIO.StringIO()
    im.save(handle, 'ppm')
    buffer = handle.getvalue()
    loader = gtk.gdk.PixbufLoader('pnm')
    loader.write(buffer, len(buffer))
    pixbuf = loader.get_pixbuf()
    loader.close()
    return pixbuf

empty_pixbuf = pixbuf_from_pil(
        PIL.Image.new('RGB', (image_size, image_size), (255, 255, 255)))

class Image_loader:

    def __init__(self):
        # From URL to (Pixbuf, Images).  Pixbuf is None when Pixbuf is not
        # known.  Images is a list of GTK images waiting for that URL, or None
        # after the loading has completed.  (None, None) is a way to remember
        # that the image URL is invalid, and should not be loaded again.
        self.cache = {}
        # The older URL at the beginning, the most recent at the end.
        self.lru = []

    def load(self, image, url):
        # Load the GTK image from the given URL.  If not available yet,
        # then load an empty image now and manage for the real image later.
        if url in self.cache:
            pixbuf, images = self.cache[url]
            if pixbuf is None:
                if images is not None:
                    images.append(image)
                pixbuf = empty_pixbuf
            image.set_from_pixbuf(pixbuf)
            self.lru.remove(url)
            self.lru.append(url)
            return
        image.set_from_pixbuf(empty_pixbuf)
        self.cache[url] = None, [image]
        Common.gui.delay(0, self.delayed_load, url)
        self.lru.append(url)
        if len(self.lru) > image_loader_capacity:
            del self.cache[self.lru.pop(0)]

    def delayed_load(self, url):
        # Load an image from an URL and spread it on all strips where it is
        # already expected.
        pixbuf = pixbuf_from_url(url)
        if url in self.cache:
            images = self.cache[url][1]
            self.cache[url] = pixbuf, None
            for image in images:
                image.set_from_pixbuf(pixbuf)

image_loader = Image_loader()
