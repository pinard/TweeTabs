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
A Twitter reader and personal manager - Common definitions.
"""

from xml.sax.saxutils import escape

import pygtk
pygtk.require('2.0')

class Error(Exception):
    pass

# The TweeTabs configuration directory, patched in from Main.
configdir = None

# If threading should be used, patched in from Main.
threaded = False

# The single instance of the Gui, patched in from Main.
gui = None

# The single instance of the Twitter manager, patched in from Main.
manager = None

# The following two functions are pretty central, in the TweeTabs machinery,
# for relieving the need of Python threads.  This is worth a few words ☺.
# The "launch" function has the purpose of starting a new pseudo-thread,
# represented and driven by a generator method, while the the "advance"
# function triggers some progress within the generator.

# The extra arguments to "lauch" are transmitted to the generator method.
# The generator usually does not accomplish its mission all in a row:
# it relinquishes control once in a while, giving a chance to some other
# part of the program to progress in parallel.  Once done with its work,
# the generator may either fall through its end, do "return", or "yield None".

# For relinquishing control, the generator should "yield" a special function,
# called a delaying function.  A delaying function expects as its single
# argument the iterator instance of the generator (if "gen" is a generator
# method, one uses "gen().next" to get hold on such an iterator instance);
# the delaying function returns almost immediately, yet before doing so,
# it ensures that the iterator will be "advance"d at some later time.

# Some delaying functions are already programmed.  The "gui.early" delaying
# function is usable when the pseudo-thread wants the control back as early as
# possible, once the other pseudo-threads will have got some chance to run.
# The "manager.delay" delaying function is usable before some results are
# requested from the Twitter site, when the request is accountable against
# the rate limits set by the site, the manager guarantees some delay meant
# to slow down the pace of requests.  There is also a "gui.delay" function,
# which cannot be used directly as it expects two arguments: a floating
# number of seconds to wait, and the iterator.  When such timed delay is
# needed, the "gui.delay" call is wrapped within a closure fixing the value
# of its first argument, and this single argument closure is then used as
# the actual delaying function.

def launch(generator, *args, **kws):
    advance(generator(*args, **kws).next)

def advance(iterator):
    try:
        postponer = iterator()
    except StopIteration:
        return
    if postponer is not None:
        postponer(iterator)
