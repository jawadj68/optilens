from django.conf import settings


def local_pages(request):
    return {"show_install_guide": settings.INSTALL_GUIDE_TEMPLATE_PATH.is_file()}
