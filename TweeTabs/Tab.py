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
A Twitter reader and personal manager - Tab structures.
"""

__metaclass__ = type
import atexit, gtk, re, sys

import Common, Strip

class Error(Common.Error):
    pass

## Base types.

class Tab:
    ordinal = 0
    registry = {}
    name_base = None
    name = None
    strip_type = None
    frozen = False
    hidden = False
    # Values are False, True and 2 (another True for complement sets)
    selected = False

    def __init__(self, *inputs):
        Tab.ordinal += 1
        self.ordinal = Tab.ordinal
        Tab.registry[self.ordinal] = self
        self.inputs = []
        self.added = set()
        self.deleted = set()
        self.outputs = set()
        self.strips = set()
        self.visible_strip = {}
        self.create_widget()
        if self.name_base is not None:
            self.set_name(self.name_base)
        for input in inputs:
            self.add_input(input)
        self.goto()
        # Not sure why this is still needed here.
        self.refresh()

    def __str__(self):
        return type(self).__name__ + ' ' + (self.name or str(self.ordinal))

    def set_name(self, name):
        if self.name is None:
            del Tab.registry[self.ordinal]
        else:
            del Tab.registry[self.name]
            del self.name
        if name is None:
            Tab.registry[self.ordinal] = self
        else:
            if name in Tab.registry:
                match = re.match('(.*)([0-9]+)$', name)
                if match:
                    name_base = match.group(1)
                    counter = int(match.group(2))
                else:
                    name_base = name
                    counter = 1
                counter += 1
                name = name_base + str(counter)
                while name in Tab.registry:
                    counter += 1
                    name = name_base + str(counter)
            self.name = name
            Tab.registry[name] = self
        self.name = name
        self.update_tab_label()

    def close(self):
        for input in self.inputs:
            input.outputs.discard(self)
        self.inputs = []
        for output in list(self.outputs):
            self.discard_output(output)
        self.strips = set()

    def goto(self):
        page = Common.gui.notebook_widget.page_num(self.widget)
        if page >= 0:
            Common.gui.notebook_widget.set_current_page(page)

    def select(self, complement=False):
        if complement:
            wanted = 2
        else:
            wanted = True
        if self.selected != wanted:
            self.selected = wanted
            if self.hidden:
                self.unhide()
            else:
                self.update_tab_label()

    def unselect(self):
        if self.selected:
            self.selected = False
            self.update_tab_label()

    def freeze(self):
        if not self.frozen:
            self.frozen = True
            self.update_tab_label()

    def unfreeze(self):
        if self.frozen:
            self.frozen = False
            self.refresh()
            self.update_tab_label()

    def hide(self):
        if not self.hidden:
            page = Common.gui.notebook_widget.page_num(self.widget)
            assert page >= 0, self
            Common.gui.notebook_widget.remove_page(page)
            self.undisplay_strips(self.strips)
            self.hidden = True

    def unhide(self):
        if self.hidden:
            Common.gui.notebook_widget.append_page(self.widget, gtk.Label())
            Common.gui.notebook_widget.set_tab_reorderable(self.widget, True)
            self.display_strips(self.strips)
            self.hidden = False

    def add_input(self, tab):
        if self.strip_type is None:
            self.strip_type = tab.strip_type
        elif not issubclass(tab.strip_type, self.strip_type):
            raise Error("%s is not made of %s strips"
                        % (tab, self.strip_type.__name__))
        tab.add_output(self)

    def discard_input(self, tab):
        tab.discard_output(self)

    def add_output(self, tab):
        self.outputs.add(tab)
        if self not in tab.inputs:
            tab.inputs.append(self)
            if not tab.frozen:
                tab.refresh()

    def discard_output(self, tab):
        self.outputs.discard(tab)
        if self in tab.inputs:
            tab.inputs.remove(self)
            if not tab.frozen:
                tab.refresh()

    def refresh(self):
        strips = (self.recomputed_strips() | self.added) - self.deleted
        self.discard_strips(self.strips - strips)
        self.add_strips(strips)

    def recomputed_strips(self):
        # Shall be defined in derived classes.
        raise NotImplementedError

    def allowable_strips(self, strips):
        # Shall be defined in derived classes.
        raise NotImplementedError

    def add_strips(self, strips):
        strips = self.allowable_strips(strips) - self.strips
        self.strips |= strips
        for output in self.outputs:
            if not output.frozen:
                output.add_strips(strips)
        if not self.hidden:
            self.display_strips(strips)
        return strips

    def discard_strips(self, strips):
        strips = strips & self.strips
        self.strips -= strips
        for output in self.outputs:
            if not output.frozen:
                output.discard_strips(strips)
        if not self.hidden:
            self.undisplay_strips(strips)
        return strips

    def display_strips(self, strips):
        for strip in sorted(strips):
            visible_strip = strip.visible_maker(self, strip)
            self.visible_strip[strip] = visible_strip
            self.tab_vbox.pack_start(visible_strip.widget, False, False)
        self.update_tab_label()

    def undisplay_strips(self, strips):
        for strip in reversed(sorted(strips)):
            self.tab_vbox.remove(self.visible_strip[strip].widget)
            del self.visible_strip[strip]
        self.update_tab_label()

    def create_widget(self):
        window = gtk.ScrolledWindow()
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        vbox = self.tab_vbox = gtk.VBox(False, Common.gui.spacing)
        window.add_with_viewport(vbox)
        window.show_all()
        Common.gui.notebook_widget.append_page(window, gtk.Label())
        Common.gui.notebook_widget.set_tab_reorderable(window, True)
        self.widget = window

    def update_tab_label(self):
        text = '<span'
        if self.selected:
            if self.selected == 2:
                text += ' foreground="' + Common.gui.select2_color + '"'
            else:
                text += ' foreground="' + Common.gui.select_color + '"'
        if self.name is None:
            name = '%d' % self.ordinal
            text += ' style="italic"'
        else:
            name = self.name
        if not self.frozen:
           text += ' weight="bold"'
        text += ('>' + Common.escape(name) + '</span>'
                 ' <span size="small" foreground="gray50">'
                 + str(len(self.tab_vbox.get_children()))
                 + '</span>')
        label = gtk.Label()
        label.set_markup(text)
        Common.gui.notebook_widget.set_tab_label(self.widget, label)

class Preset(Tab):

    def __init__(self):
        self.preset_strips = set()
        Tab.__init__(self)

    def add_input(self):
        raise NotImplementedError

    def discard_input(self):
        raise NotImplementedError

    def recomputed_strips(self):
        return self.preset_strips

    def allowable_strips(self, strips):
        return strips & self.preset_strips

class Periodic(Preset):
    period = None
    capacity = 200

    def __init__(self):
        Preset.__init__(self)
        Common.gui.early(self.reload_generator().next)

    def reload_generator(self):

        def error_delay(iterator):
            Common.gui.delay(10, iterator)

        def normal_delay(iterator):
            Common.gui.delay(self.period, iterator)

        while True:
            try:
                self.reload()
            except Common.Error, exception:
                yield error_delay
            else:
                yield normal_delay
                yield Common.manager.delay

    def reload(self):
        # Shall be defined in derived classes.
        raise NotImplementedError

    def refresh(self):
        if self.capacity is not None:
            if len(self.preset_strips) > self.capacity:
                self.preset_strips = set(
                        sorted(self.preset_strips)[-self.capacity:])
        Preset.refresh(self)

class Union(Tab):
    name_base = 'Union'

    def recomputed_strips(self):
        strips = set()
        for input in self.inputs:
            strips |= input.strips
        return strips

    def allowable_strips(self, strips):
        unwanted = set(strips)
        for input in self.inputs:
            unwanted -= input.strips
        return strips - unwanted

class Closeable(Union):
    modified = False

    def close(self):
        if self.modified:
            self.save_strips()
        Union.close(self)

    def add_strips(self, strips):
        strips = Union.add_strips(self, strips)
        if strips and not self.modified:
            self.modified = True
            atexit.register(self.close)
        return strips

    def discard_strips(self, strips):
        strips = Union.discard_strips(self, strips)
        if strips and not self.modified:
            self.modified = True
            atexit.register(self.close)
        return strips

## Final types.

class Difference(Tab):
    name_base = 'Diff'

    def add_output(self, tab):
        negative = set(self.inputs[1:])
        seen = set()
        stack = set(tab.outputs)
        while stack:
            top = stack.pop()
            if top in negative:
                raise Error("Negative loop in tab plumbing")
            seen.add(top)
            for output in top.outputs:
                if output not in seen:
                    stack.append(output)
        Tab.add_output(self, tab)

    def recomputed_strips(self):
        strips = set()
        if self.inputs:
            strips |= self.inputs[0].strips
            for input in self.inputs[1:]:
                self.strips -= input.strips
        return strips

    def allowable_strips(self, strips):
        strips &= self.inputs[0].strips
        for input in self.inputs[1:]:
            strips -= input.strips
        return strips

class Direct_timeline(Periodic):
    strip_type = Strip.Tweet
    name_base = 'Direct'
    period = 3 * 60

    def reload(self):
        return Common.manager.load_direct_timeline(self)

class Direct_sent_timeline(Periodic):
    strip_type = Strip.Tweet
    name_base = 'DSent'
    period = 60 * 60

    def reload(self):
        return Common.manager.load_direct_sent_timeline(self)

class Followers(Periodic):
    strip_type = Strip.User
    name_base = '…ers'
    capacity = None
    period = 60 * 60

    def reload(self):
        return Common.manager.fetch_followers(self)

class Following(Periodic):
    strip_type = Strip.User
    name_base = '…ing'
    capacity = None
    period = 60 * 60

    def reload(self):
        return Common.manager.fetch_following(self)

class Friends_timeline(Periodic):
    strip_type = Strip.Tweet
    name_base = 'Friends'
    period = 10 * 60

    def reload(self):
        return Common.manager.load_friends_timeline(self)

class Id_input(Preset):

    def __init__(self, file_name):
        self.file_name = file_name
        Preset.__init__(self)
        try:
            lines = file(self.file_name)
        except IOError, exception:
            raise Error(str(exception))
        else:
            for line in lines:
                line = line.rstrip()
                if line:
                    strip = Strip.Strip(line)
                    self.preset_strips.add(strip)
        self.add_strips(self.preset_strips)

class Id_output(Closeable):

    def __init__(self, file_name, *inputs):
        self.file_name = file_name
        Closeable.__init__(self, *inputs)

    def save_strips(self):
        write = file(self.file_name, 'w').write
        for strip in sorted(self.strips):
            write(str(strip) + '\n')

class Interactive(Tab):

    def __init__(self, values):
        self.preset_strips = set(map(Strip.Strip, values))
        Tab.__init__(self)

    def recomputed_strips(self):
        return self.preset_strips

    def allowable_strips(self, strips):
        return strips & self.preset_strips

class Intersection(Tab):
    name_base = 'Inter'

    def recomputed_strips(self):
        strips = set()
        if self.inputs:
            strips |= self.inputs[0].strips
            for input in self.inputs[1:]:
                strips &= input.strips
        return strips

    def allowable_strips(self, strips):
        for input in self.inputs:
            strips &= input.strips
        return strips

class Public_timeline(Periodic):
    strip_type = Strip.Tweet
    name_base = 'Public'
    period = 2 * 60

    def reload(self):
        return Common.manager.load_public_timeline(self)

class Replies_timeline(Periodic):
    strip_type = Strip.Tweet
    name_base = 'Replies'
    period = 2 * 60

    def reload(self):
        return Common.manager.load_replies_timeline(self)

class User_timeline(Periodic):
    strip_type = Strip.Tweet
    period = 4 * 60

    def __init__(self):
        import Manager
        self.name_base = Manager.user.capitalize()
        Periodic.__init__(self)

    def reload(self):
        return Common.manager.load_user_timeline(self)
