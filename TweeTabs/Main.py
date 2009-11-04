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
A Twitter reader and personal manager.

Usage: tweetabs [OPTION]...

Options:
  -h                Print this help and exit
  -g WIDTHxHEIGHT   Set minimum geometry (default 300x200)
  -c CONFIG_DIR     Configuration directory (default ~/.tweetabs)
  -n                Do not use any default tab setup

Debugging options:
  -r   Read-only mode, no tweet sending, no destructive operations
  -t   Use a separate thread for the Twitter manager
  -i   Stay in Python when the program exits
"""

__metaclass__ = type
import gobject, gtk, os, sys

import Common, Scheduler

class Main:
    initial_tabsetup = True
    geometry = None
    read_only_mode = None

    def main(self, *arguments):

        # Decode options.
        import getopt
        options, arguments = getopt.getopt(arguments, 'c:hig:nrt')
        for option, value in options:
            if option == '-c':
                Common.configdir = value
            elif option == '-h':
                sys.stdout.write(__doc__)
                return
            elif option == '-i':
                os.putenv('PYTHONINSPECT', '1')
            elif option == '-g':
                self.geometry = value
            elif option == '-n':
                self.initial_tabsetup = False
            elif option == '-r':
                self.read_only_mode = True
            elif option == '-t':
                Common.threaded = True
        if Common.configdir is None:
            Common.configdir = os.path.expanduser('~/.tweetabs')

        # Should only be imported after option decoding.
        import Gui, Twitter, Strip, Tab

        # Push some options into Gui.
        if self.geometry is not None:
            width, height = map(int, self.geometry.split('x'))
            Gui.Gui.minimum_width = width
            Gui.Gui.minimum_height = height
        if self.read_only_mode is not None:
            Gui.Gui.read_only_mode = True

        # Read in default initialization as set by user.
        if os.path.exists(Common.configdir + '/defaults.py'):
            context = {'Gui': Gui.Gui, 'Strip': Strip, 'Twitter': Twitter}
            execfile(Common.configdir + '/defaults.py', context, {})
        if Twitter.user is None or Twitter.password is None:
            sys.exit("Twitter user not set, set it in your defaults.py file.")

        # Prepare the GUI (first), then the Twitter manager.
        Common.gui = Gui.Gui()
        if Common.threaded:
            Common.twitter = Twitter.Threaded_Twitter()
        else:
            Common.twitter = Twitter.Twitter()
        Scheduler.Thread(self.get_auth_limit_thread())
        Scheduler.Thread(self.get_ip_limit_thread())

        # Read in initial tab setup as set by user.
        if self.initial_tabsetup:
            if os.path.exists(Common.configdir + '/tabsetup.py'):
                context = dict(Tab.__dict__)
                context['configdir'] = Common.configdir
                context['delay'] = Scheduler.scheduler.delay
                execfile(Common.configdir + '/tabsetup.py', context, {})
            else:
                user = Tab.User_timeline()
                user.hide()
                replies = Tab.Replies_timeline()
                replies.hide()
                me = Tab.Union(user, replies)
                me.set_name("Me…")
                friends = Tab.Friends_timeline()
                friends.set_name("Friends")
                user.goto()

        # Start the Twitter manager (first), then the GUI.
        if Common.threaded:
            Common.twitter.start()
        try:
            Common.gui.start()
        except KeyboardInterrupt:
            pass
        if Common.threaded:
            try:
                Common.twitter.enqueue(Common.twitter.quit)
                Common.twitter.join()
            except KeyboardInterrupt:
                pass

    def get_auth_limit_thread(self):
        yield 0
        while True:
            try:
                Common.twitter.get_auth_limit()
            except Common.Error:
                yield 20
            else:
                yield 120

    def get_ip_limit_thread(self):
        yield 0
        while True:
            try:
                Common.twitter.get_ip_limit()
            except Common.Error:
                yield 20
            else:
                yield 179
 
run = Main()
main = run.main

if __name__ == '__main__':
    main(*sys.argv[1:])
