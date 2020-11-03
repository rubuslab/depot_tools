import traceback

from lib import pages


def process_page(request):
  try:
    params = request.get_json(force=True, silent=True)
    path = params['path']
    page_type = params['type']
    private = params['private']

    return pages.process_page(path, page_type, private)
  except:
    traceback.print_exc()
    return traceback.format_exc(), 200
