import previews
import simplejson as json

from datetime import date, timedelta
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, Template
from django.template.loader import get_template
from django.views.decorators.cache import never_cache
from imageutil import ImageFormatter
from models import *
from util import *

BANNER_SIZE= 5
PAGE_SIZE = 10
METADATA_CACHE_SECONDS = 3600 * 12

def can_vote(poll, request):
    if not poll.active() or not request.session.get('valid'):
        return False
    return not request.session.get('poll_%i' % poll.id)

def register_voter(poll, request):
    request.session['poll_%i' % poll.id] = True

@never_cache
def poll_view(request):
    request.session['valid'] = True
    polls = Poll.objects.filter(stop_date__gte=date.today())
    polls = [(poll, can_vote(poll, request)) for poll in polls]
    return render_to_response('poll_bar.html', locals())

def _poll_vote(request):
    choice = get_object_or_404(Choice, id=request.GET['choice'])
    poll = choice.parent
    if can_vote(poll, request):
        register_voter(poll, request)
        choice.count += 1
        choice.save()
    polls = Poll.objects.filter(stop_date__gte=date.today())
    polls = [(p, can_vote(p, request) and p != poll, False) for p in polls]
    return render_to_response('poll_bar.html', locals())

def _poll_results(request):
    poll = get_object_or_404(Poll, id=request.GET['poll'])
    polls = Poll.objects.filter(stop_date__gte=date.today())
    polls = [(p, can_vote(p, request), p == poll and 'r') for p in polls]
    return render_to_response('poll_bar.html', locals())

@never_cache
def poll_results(request):
    if 'choice' in request.GET:
        return _poll_vote(request)
    if 'poll' in request.GET:
        return _poll_results(request)
    raise Http404

def pollhist(request):
    polls = Poll.objects.filter(stop_date__lt=date.today())
    objs = [(poll, poll.choice_set.all()) for poll in polls]
    return render_json('Old polls', 'poll_history.html', locals())

def staticpage(request, slug):
    obj = get_object_or_404(StaticPage, slug=slug)
    return HttpResponse(
        json.dumps({'html': obj.html, 'title': 'Nexus | %s' % obj.title}),
        mimetype='application/json'
    )
    
def frontpage(request, title='The Nexus', content=None, page=1, static=False, author=None, tagged=None):
    DISABLE_GOOGLE = settings.DISABLE_GOOGLE
    MEDIA_URL = settings.MEDIA_URL
    FOOTER = InfoPage.objects.all()
    sidelinks = SideBarLink.objects.all()
    all_articles = visible(Article.objects)
    should_hide_banner = page != 1
    if tagged:
        all_articles = all_articles.filter(tags=tagged)
        should_hide_banner = True
    elif author:
        all_articles = all_articles.filter(authors=author)
        should_hide_banner = True
    types = (('tag-3', 
            [ tag for tag in Tag.objects.filter(type=3) if visible(tag.article_set).count() > 0 ]
        ), ('tag-2',
            [ tag for tag in Tag.objects.filter(type=2) if visible(tag.article_set).count() > 0 ]
        ), ('tag-1',
            [ tag for tag in Tag.objects.filter(type=1) if visible(tag.article_set).count() > 0 ]
        ))
    if not tagged and not author:
        banner_articles = all_articles.all()[:5]
        all_articles = all_articles.all()[5:]
    if not content:
        paginator = Paginator(all_articles, PAGE_SIZE)
        pages = paginator.num_pages
        if page > pages or page < 1:
            raise Http404
        if pages > 1:
            is_paginated = True
            page_numbers, jump_forward, jump_back = pagesof(page, pages)
            previous = page - 1
            next = page + 1
            has_next = (page < pages)
            has_previous = (page > 1)
            # the bottom one
            page_numbers2, jump_forward2, jump_back2 = pagesof(page, pages, 5)
        articles = paginator.page(page).object_list
    try:
        current_issue = visible(Issue.objects)[0]
    except IndexError:
        current_issue = False
    return HttpResponse(get_template('frontpage.html').render(Context(locals())))

def some_frontpage(request):
    return frontpage(request)

def articles(request, page):
    title = 'The Nexus' if page == 1 else 'The Nexus | %s' % page
    return frontpage(request, page=int(page), title=title)

def articles_by_tag(request, tag, page):
    title = 'The Nexus' if page == 1 else 'The Nexus | %s' % page
    tag = get_object_or_404(Tag, slug=tag)
    return frontpage(request, page=int(page), title=title, tagged=tag)

def articles_by_author(request, author, page):
    title = 'The Nexus' if page == 1 else 'The Nexus | %s' % page
    author = get_object_or_404(Author, slug=author)
    return frontpage(request, page=int(page), title=title, author=author)

def imageview(request, slug):
    MEDIA_URL = settings.MEDIA_URL
    FOOTER = InfoPage.objects.all();
    obj = get_object_or_404(Image, slug=slug)
    return render_json("Image: " + obj.slug, 'imageview.html', locals())

def staff_auto_infopage(request):
    MEDIA_URL = settings.MEDIA_URL
    FOOTER = InfoPage.objects.all();
    info = get_object_or_404(InfoPage, slug='staff')
    pool = Author.objects.filter(retired=False, nexus_staff=True).all()
    titles = []
    groups = []
    for t in Title.objects.all():
        authors_for_title = [ [author, []] for author in pool.filter(title=t) ]
        if authors_for_title:
            titles.append((t.plural_form if len(authors_for_title) > 1 and t.plural_form else t, authors_for_title))
            for author in authors_for_title:
                for group in author[0].grouping.all():
                    if group.nexus_staff and not group.retired:
                        if group not in groups:
                            groups.append(group)
                        author[1].append(groups.index(group) + 1)
    return render_json(info.title, 'staff.html', locals())

def infopage(request, slug):
    MEDIA_URL = settings.MEDIA_URL
    FOOTER = InfoPage.objects.all();
    info = get_object_or_404(InfoPage, slug=slug)
    return render_json(info.title, 'info.html', locals())

def _articlepage(request, article):
    template = Template(article.custom_template.template) \
        if article.custom_template else get_template('article.html')
    html = template.render(Context(
        {'article': article, 'MEDIA_URL': settings.MEDIA_URL,
         'FOOTER': InfoPage.objects.all()}
    ))
    html = ImageFormatter(html, article.images.all()).format()
    return HttpResponse(json.dumps({'html': html, 'title': article.title}), mimetype='application/json')

def articlepage(request, year, month, slug):
    article = get_object_or_404(Article, slug=slug)
    if article.date.year != int(year) or article.date.month != int(month):
        raise Http404
    return _articlepage(request, article)

def tagpage(request, slug):
    FOOTER = InfoPage.objects.all();
    MEDIA_URL = settings.MEDIA_URL
    tag = get_object_or_404(Tag, slug=slug)
    articles = visible(tag.article_set).filter(image_centric=False)
    return render_json(tag.name, 'tag.html', locals())

def all_authors(request):
    MEDIA_URL = settings.MEDIA_URL
    FOOTER = InfoPage.objects.all();
    info = get_object_or_404(InfoPage, slug='all-staff')
    pool = Author.objects.all()
    titles = []
    groups = []
    for t in Title.objects.all():
        authors_for_title = [ [author, []] for author in pool.filter(title=t) ]
        if authors_for_title:
            titles.append((t.plural_form if len(authors_for_title) > 1 and t.plural_form else t, authors_for_title))
            for author in authors_for_title:
                for group in author[0].grouping.all():
                    if group not in groups:
                        groups.append(group)
                    author[1].append(groups.index(group) + 1)
    return render_json(info.title, 'staff.html', locals())

def authorimages(request, slug):
    FOOTER = InfoPage.objects.all();
    MEDIA_URL = settings.MEDIA_URL
    author = get_object_or_404(Author, slug=slug)
    # XXX probably should do this with queryset instead
    images_all = author.image_set.all()
    images = []
    images_nc = []
    for image in images_all:
        if image.caption or image.article_set.count():
            images.append(image)
        else:
            images_nc.append(image)
    return render_json("Images by %s" % author.name, 'authorimages.html', locals())

def tag_data(articles, selected_tags, min_date, max_date, author):
    key = 'tag_data' + str((selected_tags, min_date, max_date, author))
    cached = cache.get(key)
    if cached:
        return cached
    alltags = {}
    for article in articles:
        for tag in article.tags.all():
            if tag in alltags:
                alltags[tag] += 1
            else:
                alltags[tag] = 1
    total = articles.count()
    ret = [(tag.slug, tag in selected_tags or alltags[tag] != total) for tag in alltags.keys()]
    cache.set(key, ret, METADATA_CACHE_SECONDS)
    return ret

def dates_of(articles, tags, author):
    key = 'date_of' + str((tags,author))
    cached = cache.get(key)
    if cached:
        return cached
    ret = list(set([article.date.strftime('%Y%m') for article in articles.all()]))
    cache.set(key, ret, METADATA_CACHE_SECONDS)
    return ret

def month_end(d):
    '''Takes a datetime.date and returns the date for the last day in the
    same month.'''
    return date(d.year if d.month < 12 else d.year + 1, d.month+1 if d.month < 12 else 1, d.day) - timedelta(1)

def wrap(function):
    def wrapped(*args):
        response = json.loads(function(*args).content)
        return frontpage(args[0], title=response['title'], content=response['html'])
    return wrapped

def snippet(article):
    key = 'snippet' + str(article.id)
    cached = cache.get(key)
    if cached:
        return cached
    ret = get_template('article_snippet.html').render(Context({'article': article}))
    cache.set(key, ret)
    return ret

@staff_member_required
def preview(request, type, object_id):
    try:
        return getattr(previews, '_preview_' + type)(request, object_id)
    except AttributeError:
        raise Http404
