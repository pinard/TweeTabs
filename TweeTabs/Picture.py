#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 2009 Progiciels Bourbeau-Pinard inc.
# François Pinard <pinard@iro.umontreal.ca>, 2009.

"""\
Try TwitPic.
"""

__metaclass__ = type
import sys

class Main:

    def main(self, *arguments):
        import getopt
        options, arguments = getopt.getopt(arguments, '')
        for option, valeur in options:
            pass
        self.essai()

    def essai(self):
        import urllib, urllib2
        #image = file('/home/pinard/ss.png').read()
        #image = file('/home/pinard/fp/web/src/logo.png').read()
        image = file('/home/pinard/.thumbnails/normal/851035c2c473c95bd549a654445e75a1.png', 'rb').read()
        data = urllib.urlencode({
            'username': 'icule',
            'password': '*---*',
            'media': image})
        print data, type(data)
        #handle = urllib2.urlopen('http://twitpic.com/api/upload', data)
        #print handle
        #buffer = handle.read()
        #print buffer

run = Main()
main = run.main

if __name__ == '__main__':
    main(*sys.argv[1:])
