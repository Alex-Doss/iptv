# -*- coding: utf-8 -*-
import sys
import os
import json
import urllib
import urllib2

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
if not os.path.exists(PROFILE):
    os.makedirs(PROFILE)

HANDLE = int(sys.argv[1])
SOURCES = [
    ('ua', u'Украинские каналы', 'https://iptv-org.github.io/iptv/countries/ua.m3u', u'[UA] '),
    ('ukr', u'Каналы на украинском', 'https://iptv-org.github.io/iptv/languages/ukr.m3u', u'[UA] '),
    ('eur', u'Европейские каналы', 'https://iptv-org.github.io/iptv/regions/eur.m3u', u'[EU] '),
    ('all', u'Все каналы', 'https://iptv-org.github.io/iptv/index.m3u', u''),
    ('freeua', u'Free-TV Украина', 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_ukraine.m3u8', u'[UA] '),
]
FAV_FILE = os.path.join(PROFILE, 'favorites.json')
LOCAL_DIRS = [
    '/storage/emulated/0/Download', '/sdcard/Download', '/mnt/sdcard/Download',
    '/storage/usbhost1', '/storage/usbhost0', '/mnt/usb_storage', '/mnt/usbhost1', '/mnt/usbhost0'
]


def _u(v):
    try:
        if isinstance(v, unicode):
            return v
        return v.decode('utf-8')
    except Exception:
        try:
            return unicode(v, 'utf-8', 'ignore')
        except Exception:
            return unicode(str(v), 'utf-8', 'ignore')


def build_url(query):
    return sys.argv[0] + '?' + urllib.urlencode(query)


def cache_path(key):
    return os.path.join(PROFILE, key + '.m3u')


def fetch_url_insecure(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    try:
        import ssl
        ctx = ssl._create_unverified_context()
        response = urllib2.urlopen(req, timeout=30, context=ctx)
    except Exception:
        response = urllib2.urlopen(req, timeout=30)
    data = response.read()
    if not isinstance(data, str):
        data = data.encode('utf-8')
    return data


def read_file(path):
    f = open(path, 'r')
    data = f.read()
    f.close()
    return data


def write_file(path, data):
    f = open(path, 'w')
    f.write(data)
    f.close()


def local_candidates(key):
    names = [key + '.m3u', key + '.m3u8']
    out = []
    for d in LOCAL_DIRS:
        for name in names:
            out.append(os.path.join(d, name))
    return out


def load_favorites():
    if not os.path.exists(FAV_FILE):
        return []
    try:
        data = json.loads(read_file(FAV_FILE))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_favorites(items):
    write_file(FAV_FILE, json.dumps(items))


def add_favorite(title, url):
    items = load_favorites()
    for it in items:
        if it.get('url') == url:
            return False
    items.append({'title': title, 'url': url})
    save_favorites(items)
    return True


def remove_favorite(url):
    items = [it for it in load_favorites() if it.get('url') != url]
    save_favorites(items)


def parse_m3u(data, prefix=u''):
    channels = []
    current_name = None
    for raw_line in data.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF:'):
            if ',' in line:
                current_name = _u(line.split(',', 1)[1].strip())
            else:
                current_name = u'Без названия'
        elif line.startswith('http://') or line.startswith('https://'):
            if current_name:
                channels.append({'title': prefix + current_name, 'url': line})
                current_name = None
    return channels


def get_source(key):
    for item in SOURCES:
        if item[0] == key:
            return item
    return None


def load_source_data(key):
    src = get_source(key)
    if not src:
        raise Exception('Unknown source: ' + key)
    _, _, url, _prefix = src
    errors = []
    cp = cache_path(key)
    try:
        data = fetch_url_insecure(url)
        write_file(cp, data)
        return data, 'remote'
    except Exception as e:
        errors.append('remote: %s' % e)
    if os.path.exists(cp):
        try:
            return read_file(cp), 'cache'
        except Exception as e:
            errors.append('cache: %s' % e)
    for path in local_candidates(key):
        if os.path.exists(path):
            try:
                return read_file(path), 'local'
            except Exception as e:
                errors.append('local %s: %s' % (path, e))
    raise Exception('; '.join(errors))


def add_item(title, query, folder=True, playable=False):
    li = xbmcgui.ListItem(_u(title))
    if playable:
        li.setProperty('IsPlayable', 'true')
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, folder)


def show_root():
    add_item(u'Избранное', {'action': 'favorites'})
    add_item(u'Обновить все плейлисты', {'action': 'refresh'})
    for key, label, _url, _prefix in SOURCES:
        add_item(label, {'action': 'list', 'src': key})
    xbmcplugin.endOfDirectory(HANDLE)


def list_source(key):
    src = get_source(key)
    if not src:
        xbmcgui.Dialog().ok('UA IPTV', 'Источник не найден')
        xbmcplugin.endOfDirectory(HANDLE, False)
        return
    _key, label, _url, prefix = src
    try:
        data, mode = load_source_data(key)
        channels = parse_m3u(data, prefix)
    except Exception as e:
        xbmcgui.Dialog().ok('UA IPTV', 'Не удалось загрузить плейлист:
%s' % _u(e))
        xbmcplugin.endOfDirectory(HANDLE, False)
        return
    fav_urls = set([it.get('url') for it in load_favorites()])
    for ch in channels:
        title = ch['title']
        url = ch['url']
        if url in fav_urls:
            title = u'★ ' + title
        add_item(title, {'action': 'play', 'title': title, 'url': url}, folder=False, playable=True)
    xbmcplugin.setPluginCategory(HANDLE, label + u' [' + _u(mode) + u']')
    xbmcplugin.endOfDirectory(HANDLE)


def list_favorites():
    items = load_favorites()
    if not items:
        xbmcgui.Dialog().notification('UA IPTV', 'Избранное пусто', xbmcgui.NOTIFICATION_INFO, 3000)
    for it in items:
        add_item(u'★ ' + _u(it.get('title', 'Канал')), {'action': 'play', 'title': _u(it.get('title', 'Канал')), 'url': it.get('url', '')}, folder=False, playable=True)
    xbmcplugin.endOfDirectory(HANDLE)


def refresh_all():
    ok = 0
    fail = []
    for key, label, _url, _prefix in SOURCES:
        try:
            data = fetch_url_insecure(_url)
            write_file(cache_path(key), data)
            ok += 1
        except Exception as e:
            fail.append('%s: %s' % (label, e))
    msg = 'Обновлено: %d/%d' % (ok, len(SOURCES))
    if fail:
        msg += '

Ошибки:
' + '
'.join(fail[:4])
    xbmcgui.Dialog().ok('UA IPTV', _u(msg))
    xbmc.executebuiltin('Container.Refresh')


def context_favorite(title, url):
    favs = load_favorites()
    exists = False
    for it in favs:
        if it.get('url') == url:
            exists = True
            break
    if exists:
        remove_favorite(url)
        xbmcgui.Dialog().notification('UA IPTV', 'Удалено из избранного', xbmcgui.NOTIFICATION_INFO, 2500)
    else:
        add_favorite(title, url)
        xbmcgui.Dialog().notification('UA IPTV', 'Добавлено в избранное', xbmcgui.NOTIFICATION_INFO, 2500)


def play_stream(title, stream_url):
    title = _u(title)
    dialog = xbmcgui.Dialog()
    choice = dialog.select(title, [u'▶ Воспроизвести', u'★ Добавить/убрать избранное'])
    if choice == 1:
        context_favorite(title, stream_url)
        xbmc.executebuiltin('Container.Refresh')
        return
    li = xbmcgui.ListItem(title)
    li.setPath(stream_url)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def get_params():
    if len(sys.argv) < 3 or not sys.argv[2]:
        return {}
    query = sys.argv[2]
    if query.startswith('?'):
        query = query[1:]
    params = {}
    for pair in query.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            params[k] = urllib.unquote_plus(v)
    return params


def run():
    params = get_params()
    action = params.get('action')
    if action == 'list':
        list_source(params.get('src', 'ua'))
    elif action == 'play':
        play_stream(params.get('title', 'Канал'), params.get('url', ''))
    elif action == 'favorites':
        list_favorites()
    elif action == 'refresh':
        refresh_all()
    else:
        show_root()

if __name__ == '__main__':
    run()
