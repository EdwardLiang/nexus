from django.conf.urls.defaults import *
from django.conf import settings
from cover.views import *
from archive.views import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^nexus/', include('nexus.foo.urls')),

    # Uncomment the next line to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    (r'^admin/[^/]+/(?P<type>[^/]+)/(?P<object_id>[0-9]+)/preview/$', preview),
    (r'^admin/(.*)', admin.site.root),

    (r'^$', some_frontpage),
    (r'^ajax/poll/$', poll_results),
    (r'^ajax/poll/current$', poll_view),

    (r'^(\d{4})/(\d{2})/([-_a-zA-Z0-9]+)/$', wrap(articlepage)),
    (r'^images/([-_a-zA-Z0-9]+)$', wrap(authorimages)),
    (r'^image/([-_a-zA-Z0-9]+)/$', wrap(imageview)),
    (r'^tag/([-_a-zA-Z0-9]+)$', wrap(tagpage)),
    (r'^info/all-staff$', wrap(all_authors)),
    (r'^info/staff$', wrap(staff_auto_infopage)),
    (r'^info/([-_a-zA-Z0-9]+)$', wrap(infopage)),
    (r'^static/([-_a-zA-Z0-9]+)$', wrap(staticpage)),
    (r'^poll_history$', wrap(pollhist)),
    (r'^archive/$', wrap(issue_gallery)),
    (r'^archive-b/$', wrap(issue_gallery_b)),
    (r'^archive/current/$', wrap(current_page_gallery)),
    (r'^archive/(\d{4}-\d{2}-\d{2})/$', wrap(page_gallery)),
    (r'^tag/([-_a-zA-Z0-9]+)/(\d+)$', articles_by_tag),
    (r'^author/([-_a-zA-Z0-9]+)/(\d+)$', articles_by_author),
    (r'^(\d+)$', articles),
)

if settings.STATIC_SERVE:
    urlpatterns += patterns('',
        (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )
