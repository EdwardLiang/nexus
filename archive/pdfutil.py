import Image
from django.conf import settings
from os.path import basename, dirname, exists, getmtime
from os import makedirs, remove
from django.forms import ValidationError
from subprocess import call

JOIN_PATH = 'cache/pdf_joins/'
THUMBS_PATH = 'cache/pdf_thumbs/'
NICE = ('nice','-n15') # thumbnailing pdfs eats cpu
GS_ARGS = ['-dTextAlphaBits=4', '-dGraphicsAlphaBits=4', '-dNOPAUSE', '-dBATCH', '-sDEVICE=jpeg', '-dJPEGQ=90', '-r20', '-c', 'save pop currentglobal true setglobal false/product where{pop product(Ghostscript)search{pop pop pop revision 600 ge{pop true}if}{pop}ifelse}if{/pdfdict where{pop pdfdict begin/pdfshowpage_setpage[pdfdict/pdfshowpage_setpage get{dup type/nametype eq{dup/OutputFile eq{pop/AntiRotationHack}{dup/MediaBox eq revision 650 ge and{/THB.CropHack{1 index/CropBox pget{2 index exch/MediaBox exch put}if}def/THB.CropHack cvx}if}ifelse}if}forall]cvx def end}if}if setglobal', '-f']

def nameof(path):
    """Returns file basename stripped of file extension."""
    base = basename(path)
    index = base.rfind('.')
    return base[:index] if index > 0 else base

def mktemp(x):
    return dirname(x) + "/swp-" + basename(x)

# Not that much slower than evince especially with large (nexus) pdfs.
# Historically there were memory problems with multi-page pdfs... not anymore?
def __imagemagick_thumbnailer(input, output, size):
    """Imagemagick backend for thumbnailing a PDF."""
    swap = mktemp(output)
    call(NICE + ('convert', input, swap))
    if not exists(swap):
        command = ['gs', '-sOutputFile=%s' % swap] + GS_ARGS + [input]
        call(command)
    image = Image.open(swap) # resize AGAIN to produce consistent sizes
    image = image.convert('RGBA')
    image.thumbnail((size,2048), Image.ANTIALIAS)
    image.save(output, 'JPEG', quality=95)
    remove(swap)

#def __evince_thumbnailer(input, output, size):
#    """Evince backend for thumbnailing a PDF."""
#    swap = mktemp(output)
#    call(NICE + ('evince-thumbnailer', '-s', str(size), input, swap))
#    image = Image.open(swap) # resize AGAIN to produce consistent sizes
#    image = image.convert('RGBA')
#    image.thumbnail((size,2048), Image.ANTIALIAS)
#    image.save(output, 'JPEG', quality=95)
#    remove(swap)
#
#try:
#    from os import devnull
#    call(('evince-thumbnailer', devnull, devnull))
#    __thumbnail_backend = __evince_thumbnailer
#except OSError:
#    __thumbnail_backend = __imagemagick_thumbnailer

__thumbnail_backend = __imagemagick_thumbnailer

#from subprocess import PIPE
#def __pdftk_join(inputs, output):
#    call(('pdftk',) + tuple(inputs) + ('cat', 'output', output))

def __pypdf_join(inputs, output):
    # run in another process to avoid memory leaks
    call((dirname(__file__) + '/pypdf_join', output) + tuple(inputs))

#try:
#    call('pdftk', stdout=PIPE)
#    __join_backend = __pdftk_join
#except OSError:
#    __join_backend = __pypdf_join

__join_backend = __pypdf_join

def validate_pdf(in_memory_uploaded_file):
    ext_ok = in_memory_uploaded_file.name.endswith('.pdf')
    magic_ok = in_memory_uploaded_file.chunks().next().startswith('%PDF')
    if magic_ok and not ext_ok:
        raise ValidationError("Please rename that file so it has a .pdf extension")
    if not magic_ok and ext_ok:
        raise ValidationError("That file is only pretending to be a PDF.")
    elif not magic_ok and not ext_ok:
        raise ValidationError("That is not a PDF file.")

# it takes only a few seconds to join hundreds of pages
def joined_pdfs(input_models, id):
    """Returns url to cached union of the inputs, generating one if not available.
    Takes a list of PDF models as input."""
    maxtime = 0
    for model in input_models:
        time = getmtime(model.pdf.path)
        if time > maxtime:
            maxtime = time
    path = JOIN_PATH + '%s.pdf' % id
    output = settings.MEDIA_ROOT + path
    url = settings.MEDIA_URL + path
    if exists(output) and getmtime(output) > maxtime:
        return url
    if not exists(dirname(output)):
        makedirs(dirname(output))
    inputs = [model.pdf.path for model in input_models]
    __join_backend(inputs, output)
    return url

def pdf_to_thumbnail(input, size):
    """Returns url to cached thumbnail, generating one if not available.
    Takes an absolute path to a pdf as input.
    Tries very hard to return something sane."""
    suffix = '@%i.jpg' % size
    name = nameof(input)
    path = THUMBS_PATH + name + suffix
    output = settings.MEDIA_ROOT + path
    url = settings.MEDIA_URL + path
    if exists(output) and getmtime(output) > getmtime(input):
        return url
    if not exists(dirname(output)):
        makedirs(dirname(output))
    __thumbnail_backend(input, output, size)
    return url
