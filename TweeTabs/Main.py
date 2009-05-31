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
import os, sys

import Common, Gui, Tab
gtk = Common.gtk
gobject = Common.gobject

class Main:
    configdir = os.path.expanduser('~/.tweetabs')
    initial_tabsetup = True

    def main(self, *arguments):

        # Decode options.
        import getopt
        options, arguments = getopt.getopt(arguments, 'c:hig:nrt')
        for option, value in options:
            if option == '-c':
                self.configdir = value
            elif option == '-h':
                sys.stdout.write(__doc__)
                return
            elif option == '-i':
                os.putenv('PYTHONINSPECT', '1')
            elif option == '-g':
                width, height = map(int, value.split('x'))
                Gui.Gui.minimum_width = width
                Gui.Gui.minimum_height = height
            elif option == '-n':
                self.initial_tabsetup = False
            elif option == '-r':
                Gui.Gui.read_only_mode = True
            elif option == '-t':
                Common.threaded = True

        # Should only be imported after option decoding.
        global Manager
        import Manager

        # Read in default initialization as set by user.
        if os.path.exists(self.configdir + '/defaults.py'):
            context = {'Gui': Gui.Gui, 'Twitter': Manager}
            execfile(self.configdir + '/defaults.py', context, {})
        if Manager.user is None or Manager.password is None:
            sys.exit("Twitter user not set, set it in your defaults.py file.")

        # Prepare the GUI (first), then the Twitter manager.
        Common.gui = Gui.Gui()
        if Common.threaded:
            Common.manager = Manager.Threaded_Manager()
        else:
            Common.manager = Manager.Manager()
        gobject.timeout_add(120 * 1000, Common.manager.get_auth_limit)
        gobject.timeout_add(180 * 1000, Common.manager.get_ip_limit)
        Common.gui.delay(10, Common.manager.get_auth_limit)
        Common.gui.delay(10, Common.manager.get_ip_limit)

        # Read in initial tab setup as set by user.
        if self.initial_tabsetup:
            if os.path.exists(self.configdir + '/tabsetup.py'):
                context = dict(Tab.__dict__)
                context['configdir'] = self.configdir
                context['delay'] = Common.gui.delay
                execfile(self.configdir + '/tabsetup.py', context, {})
            else:
                tab = Tab.Friends_timeline()
                tab.set_name("Friends")

        # Start the Twitter manager (first), then the GUI.
        if Common.threaded:
            Common.manager.start()
        try:
            Common.gui.start()
        except KeyboardInterrupt:
            pass
        if Common.threaded:
            try:
                Common.manager.enqueue(Common.manager.quit)
                Common.manager.join()
            except KeyboardInterrupt:
                pass

run = Main()
main = run.main

if __name__ == '__main__':
    main(*sys.argv[1:])
