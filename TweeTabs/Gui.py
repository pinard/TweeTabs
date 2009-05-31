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
A Twitter reader and personal manager - (part of) User Interface.
"""

__metaclass__ = type
import heapq, sys, time

import Common, Tab
gtk = Common.gtk
gobject = Common.gobject

class Error(Common.Error):
    pass

def callback(func):

    def decorated(self, *args, **kws):
        self.message('')
        try:
            return func(self, *args, **kws)
        except Common.Error, exception:
            self.error(str(exception))

    return decorated

class Gui:

    # The following values may be patched in from Main.
    minimum_width = 300
    minimum_height = 200
    spacing = 7
    read_only_mode = False

    user_interface = '''\
<menubar name="MenuBar">
  <menu action="File">
    <menuitem action="File Quit"/>
  </menu>
  <menu action="Tab">
    <menuitem action="Tab Select Toggle"/>
    <menu action="Tab Configure">
      <menuitem action="Tab Configure Rename"/>
      <menuitem action="Tab Configure Toggle frozen"/>
      <menuitem action="Tab Configure Hide"/>
    </menu>
    <menu action="Tab Select">
      <menuitem action="Tab Select Add inputs"/>
      <menuitem action="Tab Select Add outputs"/>
      <menuitem action="Tab Select Clear all"/>
      <menuitem action="Tab Select Inverse"/>
      <menuitem action="Tab Select Toggle"/>
    </menu>
    <menu action="Tab Timeline">
      <menuitem action="Tab Timeline Direct"/>
      <menuitem action="Tab Timeline Direct sent"/>
      <menuitem action="Tab Timeline Friends"/>
      <menuitem action="Tab Timeline Public"/>
      <menuitem action="Tab Timeline Replies"/>
      <menuitem action="Tab Timeline User"/>
    </menu>
    <menu action="Tab Users">
      <menuitem action="Tab Users Followers"/>
      <menuitem action="Tab Users Following"/>
      <menuitem action="Tab Users Id input"/>
      <menuitem action="Tab Users Id output"/>
    </menu>
    <menu action="Tab Compose">
      <menuitem action="Tab Compose Added"/>
      <menuitem action="Tab Compose Deleted"/>
      <menuitem action="Tab Compose Difference"/>
      <menuitem action="Tab Compose Intersection"/>
      <menuitem action="Tab Compose Union"/>
    </menu>
    <separator/>
    <menuitem action="Tab Delete"/>
  </menu>
  <menu action="Strip">
  </menu>
  <menu action="Help">
  </menu>
</menubar>
'''

    def __init__(self):

        def menu_bar(window):
            manager = gtk.UIManager()
            window.add_accel_group(manager.get_accel_group())
            group = gtk.ActionGroup('Gui')
            group.add_actions([
                # Main menu.
                ('File', None, "File"),
                ('Help', None, "Help"),
                ('Strip', None, "Strip"),
                ('Tab', None, "Tab"),
                # Sub menus.
                ('Tab Compose', None, "Compose"),
                ('Tab Configure', None, "Configure"),
                ('Tab Select', None, "Select"),
                ('Tab Timeline', None, "Timeline"),
                ('Tab Users', None, "Users"),
                ])
            group.add_actions([
                ('File Quit', None, "Quit", None,
                    None, self.file_quit_cb),
                ('Tab Compose Added', None, "Added", None,
                    None, self.tab_compose_added_cb),
                ('Tab Compose Deleted', None, "Deleted", None,
                    None, self.tab_compose_deleted_cb),
                ('Tab Compose Difference', None, "Difference", None,
                    None, self.tab_compose_difference_cb),
                ('Tab Compose Intersection', None, "Intersection", None,
                    None, self.tab_compose_intersection_cb),
                ('Tab Compose Union', None, "Union", None,
                    None, self.tab_compose_union_cb),
                ('Tab Configure Hide', None, "Hide", None,
                    None, self.tab_configure_hide_cb),
                ('Tab Configure Rename', None, "Rename", None,
                    None, self.tab_configure_rename_cb),
                ('Tab Configure Toggle frozen', None, "Toggle frozen", None,
                    None, self.tab_configure_toggle_frozen_cb),
                ('Tab Delete', None, "Delete", None,
                    None, self.tab_delete_cb),
                ('Tab Select Add inputs', None, "Add inputs", None,
                    None, self.tab_select_add_inputs_cb),
                ('Tab Select Add outputs', None, "Add outputs", None,
                    None, self.tab_select_add_outputs_cb),
                ('Tab Select Clear all', None, "Clear all", None,
                    None, self.tab_select_clear_all_cb),
                ('Tab Select Inverse', None, "Inverse", None,
                    None, self.tab_select_inverse_cb),
                ('Tab Select Toggle', None, "Toggle selected", None,
                    None, self.tab_select_toggle_cb),
                ('Tab Timeline Direct', None, "Direct", None,
                    None, self.tab_timeline_direct_cb),
                ('Tab Timeline Direct sent', None, "Direct sent", None,
                    None, self.tab_timeline_direct_sent_cb),
                ('Tab Timeline Friends', None, "Friends", None,
                    None, self.tab_timeline_friends_cb),
                ('Tab Timeline Public', None, "Public", None,
                    None, self.tab_timeline_public_cb),
                ('Tab Timeline Replies', None, "Replies", None,
                    None, self.tab_timeline_replies_cb),
                ('Tab Timeline User', None, "User", None,
                    None, self.tab_timeline_user_cb),
                ('Tab Users Followers', None, "Followers", None,
                    None, self.tab_users_followers_cb),
                ('Tab Users Following', None, "Following", None,
                    None, self.tab_users_following_cb),
                ('Tab Users Id input', None, "Id input", None,
                    None, self.tab_users_id_input_cb),
                ('Tab Users Id output', None, "Id output", None,
                    None, self.tab_users_id_output_cb),
                ])
            manager.insert_action_group(group, 0)
            manager.add_ui_from_string(Gui.user_interface)
            return manager.get_widget('/MenuBar')

        def main_board():
            notebook = gtk.Notebook()
            notebook.set_tab_pos(gtk.POS_TOP)
            notebook.set_scrollable(True)
            self.notebook_widget = notebook
            return notebook

        def entry_line():
            hbox = gtk.HBox(False, self.spacing)
            entry = gtk.Entry(140)
            entry.connect('changed', self.entry_changed)
            entry.connect('activate', self.entry_activate)
            hbox.pack_start(entry, True)
            label = gtk.Label('140')
            hbox.pack_start(label, False)
            self.entry_widget = entry
            self.count_widget = label
            return hbox

        def status_line():
            self.gui_message_widget = gtk.Label()
            self.twitter_message_widget = gtk.Label()
            self.twitter_error_widget = gtk.Label()
            self.twitter_limits_widget = gtk.Label()

            hbox = gtk.HBox(False, self.spacing)
            hbox.pack_start(self.gui_message_widget, False)
            hbox.pack_end(self.twitter_limits_widget, False)
            hbox.pack_end(self.twitter_error_widget, False)
            hbox.pack_end(self.twitter_message_widget, False)
            return hbox

        self.delay_timeout_id = None
        self.delayed_events = []

        window = gtk.Window()
        window.set_title("TweeTabs")
        window.set_size_request(self.minimum_width, self.minimum_height)
        window.set_border_width(self.spacing)
        window.connect('destroy', self.destroy)
        window.connect('delete_event', self.delete_event)

        vbox = gtk.VBox(False, self.spacing)
        vbox.pack_start(menu_bar(window), False)
        vbox.pack_start(main_board(), True)
        vbox.pack_start(status_line(), False)
        vbox.pack_start(entry_line(), False)
        window.add(vbox)
        self.widget = window
      
    def start(self):
        self.widget.show_all()
        self.count_widget.hide()
        self.message('☺')
        if Common.threaded:
            gtk.gdk.threads_init()
            gtk.gdk.threads_enter()
        gtk.main()
        if Common.threaded:
            gtk.gdk.threads_leave()

    def delay(self, delta, func, *args, **kws):
        if self.delay_timeout_id is not None:
            gobject.source_remove(self.delay_timeout_id)
        if delta is None:
            delta = Common.manager.suggested_delta(self.delayed_events)
        now = time.time()
        future = now + delta
        heapq.heappush(self.delayed_events, (future, func, args, kws))
        delta = max(10, int(1000 * (self.delayed_events[0][0] - now)))
        self.delay_timeout_id = gobject.timeout_add(delta, self.delay_loop)

    def delay_loop(self):
        now = time.time()
        while self.delayed_events and now >= self.delayed_events[0][0]:
            future, func, args, kws = heapq.heappop(self.delayed_events)
            func(*args, **kws)
            self.refresh()
            now = time.time()
        if self.delayed_events:
            delta = max(10, int(1000 * (self.delayed_events[0][0] - now)))
        else:
            delta = 5000
        self.delay_timeout_id = gobject.timeout_add(delta, self.delay_loop)

    def refresh(self):
        while gtk.events_pending():
            gtk.main_iteration(False)

    ## Callbacks.

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def delete_event(self, widget, data=None):
        return False

    def entry_changed(self, widget, data=None):
        count = len(widget.get_text())
        if count == 0:
            self.count_widget.hide()
        else:
            self.count_widget.set_label(str(140 - count))
            self.count_widget.show()

    def entry_activate(self, widget, data=None):
        text = self.entry_widget.get_text().strip()
        if text:
            if self.read_only_mode:
                self.entry_widget.set_text('[unsent]')
                return
            self.delay(0, Common.manager.send_tweet, text)
        self.entry_widget.set_text('')

    @callback
    def file_quit_cb(self, action):
        gtk.main_quit()

    @callback
    def tab_compose_added_cb(self, action):
        raise Error("Not implemented yet")

    @callback
    def tab_compose_deleted_cb(self, action):
        raise Error("Not implemented yet")

    @callback
    def tab_compose_difference_cb(self, action):
        tab = self.current_tab()
        if tab is None:
            raise Error("No current tab")
        inputs = self.argument_tabs()
        if tab in inputs:
            inputs.remove(tab)
        Tab.Difference(tab, *inputs)
        self.tab_select_clear_all_cb(action)

    @callback
    def tab_compose_intersection_cb(self, action):
        Tab.Intersection(*self.argument_tabs())
        self.tab_select_clear_all_cb(action)

    @callback
    def tab_compose_union_cb(self, action):
        Tab.Union(*self.argument_tabs())
        self.tab_select_clear_all_cb(action)

    @callback
    def tab_configure_hide_cb(self, action):
        for tab in self.argument_tabs():
            tab.hide()
        self.tab_select_clear_all_cb(action)

    @callback
    def tab_configure_rename_cb(self, action):
        tab = self.current_tab()
        if tab is None:
            raise Error("No current tab")
        name = self.get_string()
        if name is None:
            return
        if name:
            tab.set_name(name)
        else:
            tab.set_name(None)

    @callback
    def tab_configure_toggle_frozen_cb(self, action):
        for tab in self.argument_tabs():
            if tab.frozen:
                tab.unfreeze()
            else:
                tab.freeze()
        self.tab_select_clear_all_cb(action)

    @callback
    def tab_delete_cb(self, action):
        raise Error("Not implemented yet")

    @callback
    def tab_select_add_inputs_cb(self, action):
        for tab in self.argument_tabs():
            if isinstance(tab, Difference):
                tab.inputs[0].select()
                for tab in tab.inputs[1:]:
                    tab.select(complement=True)
            else:
                for tab in tab.inputs:
                    tab.select()

    @callback
    def tab_select_add_outputs_cb(self, action):
        for tab in self.argument_tabs():
            for tab in tab.outputs:
                tab.select()

    @callback
    def tab_select_clear_all_cb(self, action):
        for tab in Tab.Tab.registry.itervalues():
            tab.unselect()

    @callback
    def tab_select_inverse_cb(self, action):
        for tab in Tab.Tab.registry.itervalues():
            if not tab.hidden:
                if tab.selected:
                    tab.unselect()
                else:
                    tab.select()

    @callback
    def tab_select_toggle_cb(self, action):
        tab = self.current_tab()
        if tab is None:
            raise Error("No current tab")
        if tab.selected:
            tab.unselect()
        else:
            tab.select()

    @callback
    def tab_timeline_direct_cb(self, action):
        Tab.Direct_timeline()

    @callback
    def tab_timeline_direct_sent_cb(self, action):
        Tab.Direct_sent_timeline()

    @callback
    def tab_timeline_friends_cb(self, action):
        Tab.Friends_timeline()

    @callback
    def tab_timeline_public_cb(self, action):
        Tab.Public_timeline()

    @callback
    def tab_timeline_replies_cb(self, action):
        Tab.Replies_timeline()

    @callback
    def tab_timeline_user_cb(self, action):
        Tab.User_timeline()

    @callback
    def tab_users_followers_cb(self, action):
        Tab.Followers()

    @callback
    def tab_users_following_cb(self, action):
        Tab.Following()

    @callback
    def tab_users_id_input_cb(self, action):
        name = self.get_string()
        if name is not None:
            Tab.Id_input(name)

    @callback
    def tab_users_id_output_cb(self, action):
        name = self.get_string()
        if name is not None:
            Tab.Id_output(name, *self.argument_tabs())
            self.tab_select_clear_all_cb(action)

    ## Services.

    def message(self, diagnostic):
        self.gui_message_widget.set_label(diagnostic)
        self.refresh()

    def error(self, diagnostic):
        self.gui_message_widget.set_markup(
                '<span weight="bold" foreground="red">'
                + Common.escape(diagnostic) + '</span>')
        self.refresh()

    def argument_tabs(self):
        tabs = []
        for tab in Tab.Tab.registry.itervalues():
            if tab.selected:
                tabs.append(tab)
        if not tabs:
            tab = self.current_tab() 
            if tab is not None:
                tabs.append(tab)
        return tabs

    def current_tab(self):
        page = self.notebook_widget.get_current_page()
        if page >= 0:
            widget = self.notebook_widget.get_children()[page]
            for tab in Tab.Tab.registry.itervalues():
                if tab.tab_widget is widget:
                    return tab

    def get_string(self):
        return "Allo"
        raise Error("Not implemented yet")
