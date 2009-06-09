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
A Twitter reader and personal manager - Thread handling.
"""

import gobject, heapq, random, time

import Common

class Scheduler:

    def __init__(self):
        self.create_slow_down_deltas()

    # The following function offers a way around Python threads.  It has
    # the purpose of starting a new (non-Python) thread.  The thread in this
    # case is represented and driven by a generator method.

    # The first argument is either a single lock, a list or tuple of locks,
    # or None for no lock at all.  A thread will tie all of its locks at
    # once before it starts, and untie them all after it finishes.  A thread
    # start will be postponed until all its locks are free.

    # The second argument is the generator method, and all extra arguments are
    # transmitted to the generator method when called.  The generator usually
    # does not accomplish its mission all in a row: it relinquishes control
    # once in a while, giving a chance to some other part of the program
    # to progress in parallel.  To do so, it "yield"s a special value.
    # If that value is an integer or float, this is a number of seconds
    # to wait before control returns.  If that value is True, the delay is
    # automatically chosen to slow down the pace of requests to the Twitter
    # API, as the Twitter site enforces a limit of 100 requests per hour.
    # Once done with its work, the generator may either fall through its end,
    # do "return", or "yield None".

    def launch(self, locks, generator, *args, **kws):
        if locks is None:
            locks = []
        if not isinstance(locks, (list, tuple)):
            locks = [locks]
        thread = generator(*args, **kws).next
        self.advance(thread)

    def advance(self, thread):
        try:
            delay = thread()
        except StopIteration:
            pass
        else:
            if delay is True:
                self.slow_down(thread)
                return
            if isinstance(delay, (int, float)):
                self.delay(delay, thread)
                return
            assert delay is None, delay

    # Delayed threads contains a priority queue of (Future, Thread), where
    # Future is a wanted time for resuming Thread.

    timeout_id = None
    delayed_threads = []
    within_delay_loop = False

    def delay(self, delta, thread):
        now = time.time()
        future = now + delta
        heapq.heappush(self.delayed_threads, (future, thread))
        if not self.within_delay_loop:
            if self.timeout_id is not None:
                gobject.source_remove(self.timeout_id)
            delta = max(10, int(1000 * (self.delayed_threads[0][0] - now)))
            self.timeout_id = gobject.timeout_add(delta, self.delay_loop)

    def delay_loop(self):
        self.within_delay_loop = True
        now = time.time()
        while self.delayed_threads and now >= self.delayed_threads[0][0]:
            future, thread = heapq.heappop(self.delayed_threads)
            self.advance(thread)
            Common.gui.refresh()
            now = time.time()
        if self.delayed_threads:
            delta = max(10, int(1000 * (self.delayed_threads[0][0] - now)))
        else:
            delta = 5000
        self.timeout_id = gobject.timeout_add(delta, self.delay_loop)
        self.within_delay_loop = False

    # Postponed threads contain a list of threads to resume, each after
    # some slowdown time to protect against Twitter API rate limiting.
    # These are resumed in random order instead of first in / first out,
    # as an heuristic way to give everything a more equal chance, in case
    # of lot of related threads get added in a row.

    slowed_down_threads = []
    within_slow_down_loop = False

    def slow_down(self, thread):
        self.slowed_down_threads.append(thread)
        if (not self.within_slow_down_loop
                and len(self.slowed_down_threads) == 1):
            gobject.timeout_add(self.slow_down_delta(), self.slow_down_loop)

    def slow_down_loop(self):
        self.within_slow_down_loop = True
        pick = random.randint(0, len(self.slowed_down_threads) - 1) 
        self.advance(self.slowed_down_threads.pop(pick))
        Common.manager.auth_limit -= 1
        if self.slowed_down_threads:
            gobject.timeout_add(self.slow_down_delta(), self.slow_down_loop)
        self.within_slow_down_loop = False

    def create_slow_down_deltas(self):
        a = 0
        b = 1
        deltas = []
        while len(deltas) < 11 or b < 30 * 60:
            a, b = b, a + b
            deltas.append(a)
        self.slow_down_deltas = deltas[-11:]

    def slow_down_delta(self):
        limit = max(0, min(100, Common.manager.auth_limit))
        return self.slow_down_deltas[(100 - limit) // 10]

scheduler = Scheduler()
launch = scheduler.launch
