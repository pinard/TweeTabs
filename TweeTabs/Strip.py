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
import Image, ImageDraw, StringIO
import anydbm, atexit, gtk, pango, re, simplejson, time, urllib
import twyt.data

import Common, Scheduler

image_size = 60
image_loader_capacity = 100 

# Here is the distinction between a strip and a visible strip.  A strip
# is the genuine object as included in sets, so we can do set operations.
# A widget may not have more than one parent, but the same logical strip
# may well appear in many tabs.  Moreover, a strip may be selected in a tab
# and unselected in another.  For these reasons, a visible object is really
# a strip as within a particular tab.  For each strip sub-type, there is a
# corresponding visible strip sub-type.

class Visible_strip:
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
    visible_maker = Visible_strip

    def __init__(self, key):
        self.key = key

    def __str__(self):
        return type(self).__name__ + ' ' + str(self.key)

    def __cmp__(self, other):
        return cmp(self.key, other.key)

    def __hash__(self):
        return hash(self.key)

class Visible_tweet(Visible_strip):

    def create_widget(self):

        def image():
            vbox = gtk.VBox()
            image = gtk.Image()
            image_loader.load(image, status.user)
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
                            foreground=Common.gui.url_color,
                            underline=pango.UNDERLINE_SINGLE)
                textbuffer.insert_with_tags(enditer, match.group(), tag)
                position = match.end()
            textbuffer.insert(enditer, text[position:])
            # Insert the date and source
            textbuffer.insert(enditer, '\n')
            textbuffer.insert_with_tags(
                    enditer,
                    transform_stamp(status.created_at),
                    textbuffer.create_tag(None,
                                          foreground='gray50',
                                          #size=pango.SCALE_SMALL
                                          ))
            textbuffer.insert(enditer, ', ')
            textbuffer.insert_with_tags(
                    enditer,
                    status.source,
                    textbuffer.create_tag(None,
                                          foreground='gray50',
                                          #size=pango.SCALE_SMALL,
                                          style=pango.STYLE_ITALIC))
            return textview

        status = self.strip.status

        hbox = gtk.HBox()
        hbox.pack_start(image(), False, False, Common.gui.spacing)
        eventbox = gtk.EventBox()
        eventbox.add(hbox)
        eventbox.connect('button-press-event', self.image_clicked)
        self.eventbox_widget = eventbox

        vbox = gtk.VBox()
        vbox.pack_start(eventbox, False, False)

        hbox = gtk.HBox()
        hbox.pack_start(vbox, False, False)
        hbox.pack_start(tweet())
        hbox.show_all()
        self.widget = hbox

    def image_clicked(self, widget, event):
        self.toggle_select()

    def select(self):
        if not self.selected:
            Visible_strip.select(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color(
                    Common.gui.select_color))

    def unselect(self):
        if self.selected:
            Visible_strip.unselect(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color('white'))

class Tweet(Strip):
    visible_maker = Visible_tweet

    def __init__(self, status):
        self.status = status
        Strip.__init__(self, status.id)

class Visible_user(Visible_strip):

    def create_widget(self):
        hbox = gtk.HBox()
        button = gtk.Button('☺')
        hbox.pack_start(button, False, False, Common.gui.spacing)
        label = gtk.Label(str(self.strip))
        label.set_line_wrap(True)
        hbox.pack_start(label, False, False)
        hbox.show_all()
        self.widget = hbox

    def create_widget(self):

        def image():
            vbox = gtk.VBox()
            image = gtk.Image()
            image_loader.load(image, user)
            vbox.pack_start(image, False, False)
            return vbox

        def description():
            # Prepare the display.
            textview = gtk.TextView()
            textview.set_editable(False)
            textview.set_cursor_visible(False)
            textview.set_wrap_mode(gtk.WRAP_WORD)
            textbuffer = textview.get_buffer()
            enditer = textbuffer.get_end_iter()
            # Insert the user name.
            textbuffer.insert_with_tags(
                    enditer,
                    user.screen_name + ':',
                    textbuffer.create_tag(None,
                                          foreground=Common.gui.user_color,
                                          weight=pango.WEIGHT_BOLD))
            # Insert the rest of information.
            if user.name:
                textbuffer.insert(enditer, ' ' + user.name)
            if user.location:
                textbuffer.insert(enditer, ' ')
                textbuffer.insert_with_tags(
                        enditer,
                        user.location,
                        textbuffer.create_tag(None,
                                              foreground='gray50',
                                              style=pango.STYLE_ITALIC))
            if user.description:
                textbuffer.insert(enditer, ' ' + user.description)
            if user.url:
                textbuffer.insert(enditer, ' ')
                textbuffer.insert_with_tags(
                        enditer,
                        user.url,
                        textbuffer.create_tag(None,
                                              foreground=Common.gui.url_color,
                                              underline=pango.UNDERLINE_SINGLE))
            return textview

        user = self.strip.user

        hbox = gtk.HBox()
        hbox.pack_start(image(), False, False, Common.gui.spacing)
        eventbox = gtk.EventBox()
        eventbox.add(hbox)
        eventbox.connect('button-press-event', self.image_clicked)
        self.eventbox_widget = eventbox

        vbox = gtk.VBox()
        vbox.pack_start(eventbox, False, False)

        hbox = gtk.HBox()
        hbox.pack_start(vbox, False, False)
        hbox.pack_start(description())
        hbox.show_all()
        self.widget = hbox

    def image_clicked(self, widget, event):
        self.toggle_select()

    def select(self):
        if not self.selected:
            Visible_strip.select(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color(
                    Common.gui.select_color))

    def unselect(self):
        if self.selected:
            Visible_strip.unselect(self)
            self.eventbox_widget.modify_bg(
                gtk.STATE_NORMAL,
                self.eventbox_widget.get_colormap().alloc_color('white'))

class User(Strip):
    visible_maker = Visible_user

    def __init__(self, id):
        self.user = user_loader.load(id)
        Strip.__init__(self, self.user.screen_name)

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

class Image_loader:

    def __init__(self):
        # An empty, white image is used until we get the real one.
        empty = Image.new('RGB', (image_size, image_size))
        draw = ImageDraw.Draw(empty)
        draw.rectangle([(0, 0), (image_size - 1, image_size - 1)],
                       outline=(128, 128, 128), fill=(255, 255, 255))
        self.empty_pixbuf = self.pixbuf_from_pil(empty)
        # A local database containing images, indexed by Ids.  We go to the
        # Web only when the image is not found within the database, and save
        # any obtained image within the database.
        self.db = anydbm.open(Common.configdir + '/image-cache', 'c')
        atexit.register(self.db.close)
        # From Id to (Pixbuf, Images).  Pixbuf is None when Pixbuf is not
        # known.  Images is a list of GTK images waiting for that Id, or
        # None after the loading has completed.  (None, None) is to prevent
        # load attempts, when something is permanently wrong with an Id.
        self.cache = {}
        # The older Id at the beginning, the most recent at the end.
        self.lru = []

    def load(self, image, user):
        # Load an empty image now, so the layout computes faster.
        image.set_from_pixbuf(self.empty_pixbuf)
        # Manage so the real image will replace it soon.
        Scheduler.Thread(self.load_image_thread(image, user))

    def load_image_thread(self, image, user):
        # Load the GTK image from the user Id.
        if user.id in self.cache:
            pixbuf, images = self.cache[user.id]
            if pixbuf is None:
                if images is not None:
                    images.append(image)
            else:
                image.set_from_pixbuf(pixbuf)
            self.lru.remove(user.id)
            self.lru.append(user.id)
            return
        self.cache[user.id] = None, [image]
        self.lru.append(user.id)
        if len(self.lru) > image_loader_capacity:
            del self.cache[self.lru.pop(0)]
        # Spread the image on all strips where is is already expected.
        yield 0
        pixbuf = self.pixbuf_from_user(user)
        if user.id in self.cache:
            images = self.cache[user.id][1]
            self.cache[user.id] = pixbuf, None
            for image in images:
                image.set_from_pixbuf(pixbuf)

    def pixbuf_from_user(self, user):
        # Get the raw image, either from our database or from the Web.
        id_string = str(user.id)
        if self.db.has_key(id_string):
            buffer = self.db[id_string]
        else:
            url = user.profile_image_url
            if not url:
                return self.empty_pixbuf
            url8 = url.encode('UTF-8')
            try:
                buffer = urllib.urlopen(url8).read()
            except IOError:
                try:
                    url1 = url.encode('ISO-8859-1')
                except UnicodeError:
                    return self.empty_pixbuf
                try:
                    buffer = urllib.urlopen(url1).read()
                except IOError:
                    return self.empty_pixbuf
            self.db[id_string] = buffer
        # Transform it into a PIL image.
        try:
            im = Image.open(StringIO.StringIO(buffer))
        except IOError:
            return self.empty_pixbuf
        if im.mode != 'RGB':
            im = im.convert('RGB')
        # Make it square and resize it, keeping the same center.
        sx, sy = im.size
        if sx > sy:
            extra = (sx - sy) // 2
            im = im.crop((extra, 0, extra + sy, sy))
        elif sy > sx:
            extra = (sy - sx) // 2
            im = im.crop((0, extra, sx, extra + sx))
        im = im.resize((image_size, image_size), Image.ANTIALIAS)
        # Transform the result into a pixbuf.
        return self.pixbuf_from_pil(im)

    def pixbuf_from_pil(self, im):
        handle = StringIO.StringIO()
        im.save(handle, 'ppm')
        buffer = handle.getvalue()
        loader = gtk.gdk.PixbufLoader('pnm')
        loader.write(buffer, len(buffer))
        pixbuf = loader.get_pixbuf()
        loader.close()
        return pixbuf

image_loader = Image_loader()

## User services.

class User_loader:

    def __init__(self):
        # A local database containing user descriptions, indexed by both id
        # and screen name.
        self.db = anydbm.open(Common.configdir + '/user-cache', 'c')
        atexit.register(self.db.close)

    def load(self, id):
        id_string = str(id)
        if self.db.has_key(id_string):
            buffer = self.db[id_string]
            try:
                user = simplejson.loads(buffer)
            except ValueError:
                # If anything is wrong, try auto-repairing the database.
                del self.db[id_string]
                user = None
        else:
            user = None

        if not user:

            Scheduler.Thread(self.load_user_thread(id))
            user = {'id': id,
                    'name': '',
                    'screen_name': id_string,
                    'location': None,
                    'description': None,
                    'profile_image_url': None,
                    'url': None,
                    'protected': False}

        return twyt.data.User(user)

    def load_user_thread(self, id):
        yield 0
        try:
            buffer = Common.twitter.get_user_info(id)
        except Common.Error, exception:
            pass
        else:
            if buffer:
                self.db[str(id)] = buffer

user_loader = User_loader()
