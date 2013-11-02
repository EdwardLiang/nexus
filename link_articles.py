#!/usr/local/bin/python2.5
#
# Periodic job that runs to associate Articles with Issues.
# This is necessary because often articles are posted
# before an Issue is released.
#

import sys

sys.path.append('/home/nexus/webapps/nexus/lib/python2.5')
sys.path.append('/home/nexus/lib/python2.5')

from django.core.management import setup_environ
import webfaction_settings
setup_environ(webfaction_settings)

from nexus.cover.models import *

date_map = {}

for issue in Issue.objects.all():
    date_map[issue.date] = issue

linked, unlinked = 0, 0
for article in Article.objects.filter(printed__isnull=True):
    if article.date in date_map:
        linked += 1
        print "Linking issue", article.date
        article.printed = date_map[article.date]
        article.save()
    else:
        unlinked += 1

print "Total linked", linked
print "Remaining unlinked", unlinked
