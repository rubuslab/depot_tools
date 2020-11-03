import bs4
import re


def process_issue(content):
  html = bs4.BeautifulSoup(content, features='lxml')
  _process_common(html)
  _process_patch_set_common(html.find('div', {'class': 'issue-list'}))

  for el in html.find_all('a'):
    if el.decomposed or not el.has_attr('href'):
      continue
    href = el.get('href')
    if href.startswith(('/user/', '/search?project=')):
      el.replace_with_children()
    if href.endswith('/publish'):
      el.parent.decompose()

  return html.encode('utf-8', 'ignore')


def process_patch_set(contents):
  html = bs4.BeautifulSoup(content, features='lxml')
  _process_patch_set_common(html)
  return html.encode('utf-8', 'ignore')


def process_patch(contents):
  html = bs4.BeautifulSoup(contents, features='lxml')
  _process_common(html)

  for el in html.find_all('a'):
    if el.get('href', '').startswith('/download'):
      el.decompose()

  span = html.find('span', {'text': 'Draft comments are only viewable by you.'})
  if span:
    span.decompose()
  return html.encode('utf-8', 'ignore')


def _process_common(html):
  CLOSE_STAR_ISSUE_RE = re.compile(r"^issue-(close|star)-\d+")
  REMOVED_CLASSES = (
      # Counter in gray at the top right corner.
      'counter',
      # Links to Rietveld version and RSS feeds.
      'extra',
      # Issues (see mainmenu2) and Search headers.
      'mainmenu',
      # Links to issue list pages (My Issues, Starred, Open, Closed, All).
      'mainmenu2',
      # Link to reply to an issue.
      'message-actions',
  )

  el = html.find('a', {'href': '/settings'})
  el.parent.replace_with(el.parent.find('div'))

  for el in html.find_all('div', {'class': REMOVED_CLASSES}):
    el.decompose()

  for el in html.find_all('span', {'id': CLOSE_STAR_ISSUE_RE}):
    el.decompose()

  for el in html.find_all('link', {'type': 'application/atom+xml'}):
    el.decompose()


def _process_patch_set_common(html):
  DOWNLOAD_LINKS_DIV_POS = 2
  TRYJOBS_DIV_POS = 4
  DELTA_FROM_PATCHSET_HEADER_COL = 3
  DELTA_FROM_PATCHSET_COL = 4
  DOWNLOAD_HEADER_COL = 5
  DOWNLOAD_COL = -1

  divs = html.find_all('div')
  divs[DOWNLOAD_LINKS_DIV_POS].decompose()
  if TRYJOBS_DIV_POS < len(divs):
    divs[TRYJOBS_DIV_POS].decompose()

  for tr in html.find_all('tr'):
    if tr.get('name') == 'patch':
      children = list(tr.find_all('td'))
      children[DELTA_FROM_PATCHSET_COL].decompose()
      children[DOWNLOAD_COL].decompose()
    else:
      children = list(tr.find_all('th'))
      children[DELTA_FROM_PATCHSET_HEADER_COL].decompose()
      children[DOWNLOAD_HEADER_COL].decompose()

