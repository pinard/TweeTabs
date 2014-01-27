all:
	python setup.py --quiet build

test: install
	tweetabs -c data

install: all
	python setup.py install 

ifneq "$(wildcard ~/etc/mes-sites/site.mk)" ""

site: site-all

package_name = TweeTabs
margin_color = "\#d7ebc4"
caption_color = "\#f1e4eb"

FAVICON = web/favicon.ico
LOGOURL = "/logo.png"

include ~/etc/mes-sites/site.mk

endif
