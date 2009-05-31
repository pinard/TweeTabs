# -*- coding: utf-8 -*-

# Replace both None by things like "UserName" and "UserPassword".
Twitter.user = None
Twitter.password = None

# Or even get this information from some standard place of yours.
import os
contents = file(os.path.expanduser('~/.tweetabs/user')).read()
Twitter.user, Twitter.password = contents.split()

Gui.minimum_height = 500
