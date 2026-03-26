# -*- coding: utf-8 -*-
import sys
import os
import re
import json
import time
import urllib
import urllib2

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_VERSION = ADDON.getAddonInfo('version')
ADDON_PATH = xbmc.translatePath(ADDON.getAddonInfo('path'))
PROFILE = xbmc.translatePath(ADDON.getAddonInfo('profile'))
HANDLE = int(sys.argv[1])

if not os.path.exists(PROFILE):
    try:
        os.makedirs(PROFILE)
    except Exception:
        pass

SOURCES = [
    ('ua', u'Украинские каналы', 'https://iptv-org.github.io/iptv/countries/ua.m3u', u'[UA] ', 'ua.m3u'),
    ('ukr', u'Каналы на украинском', 'https://iptv-org.github.io/iptv/languages/ukr.m3u', u'[UA] ', 'ukr.m3u'),
    ('eur', u'Европейские каналы', 'https://iptv-org.github.io/iptv/regions/eur.m3u', u'[EU] ', 'eur.m3u'),
    ('freeua', u'Free-TV Украина', 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_ukraine.m3u8', u'[UA] ', 'playlist_ukraine.m3u8'),
    ('all', u'Все каналы', 'https://iptv-org.github.io/iptv/index.m3u', u'', 'index.m3u'),
]
LOCAL_DIRS = [
    '/storage/emulated/0/Download', '/sdcard/Download', '/mnt/sdcard/Download',
    '/storage/usbhost1', '/storage/usbhost0', '/mnt/usb_storage', '/mnt/usbhost1', '/mnt/usbhost0',
    '/storage/usbotg', '/mnt/media_rw/udisk', '/storage/emulated/0', '/sdcard'
]
DEFAULT_SITES = [
    {u'title': u'YouTube', u'url': u'https://www.youtube.com/'},
    {u'title': u'MEGOGO', u'url': u'https://megogo.net/'},
    {u'title': u'Google', u'url': u'https://www.google.com/'}
]
FAV_FILE = os.path.join(PROFILE, 'favorites.json')
SITE_FILE = os.path.join(PROFILE, 'sites.json')
LOG_FILE = os.path.join(PROFILE, 'batya.log')
UPDATE_FILE = os.path.join(PROFILE, 'update_state.json')
RAW_ADDONS_XML = 'https://raw.githubusercontent.com/Alex-Doss/iptv/main/repository/addons.xml'

def _u(v):
    try:
        if isinstance(v, unicode):
            return v
        return v.decode('utf-8')
    except Exception:
        try:
            return unicode(v, 'utf-8', 'ignore')
        except Exception:
            try:
                return unicode(str(v), 'utf-8', 'ignore')
            except Exception:
                return u''

def _b(v):
    try:
        if isinstance(v, unicode):
            return v.encode('utf-8')
        return str(v)
    except Exception:
        return ''

def log_line(msg):
    try:
        text = _u(msg)
        xbmc.log(_b(u'[Для Бати] ' + text), xbmc.LOGNOTICE)
        fh = open(LOG_FILE, 'ab')
        fh.write(_b(time.strftime('%Y-%m-%d %H:%M:%S') + ' | ') + _b(text) + '\n')
        fh.close()
    except Exception:
        pass

def safe_text(path, default=u''):
    try:
        fh = open(path, 'rb')
        data = fh.read()
        fh.close()
        try:
            return data.decode('utf-8')
        except Exception:
            return data.decode('utf-8', 'ignore')
    except Exception:
        return default

def write_text(path, text):
    fh = open(path, 'wb')
    fh.write(_b(_u(text)))
    fh.close()

def read_json(path, default_obj):
    try:
        return json.loads(safe_text(path, u''))
    except Exception:
        return default_obj

def write_json(path, obj):
    write_text(path, json.dumps(obj, ensure_ascii=False))

def build_url(query):
    clean = {}
    for k in query:
        clean[k] = _b(query[k])
    return sys.argv[0] + '?' + urllib.urlencode(clean)

def get_params():
    out = {}
    if len(sys.argv) < 3 or not sys.argv[2]:
        return out
    q = sys.argv[2]
    if q.startswith('?'):
        q = q[1:]
    for part in q.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            out[k] = _u(urllib.unquote_plus(v))
    return out

def cache_path(key):
    return os.path.join(PROFILE, key + '.m3u')

def get_source(key):
    for item in SOURCES:
        if item[0] == key:
            return item
    return None

def fetch_url(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 Kodi Batya')
    try:
        import ssl
        ctx = ssl._create_unverified_context()
        resp = urllib2.urlopen(req, timeout=20, context=ctx)
    except Exception:
        resp = urllib2.urlopen(req, timeout=20)
    data = resp.read()
    try:
        return data.decode('utf-8')
    except Exception:
        return data.decode('utf-8', 'ignore')

def parse_m3u(text, prefix):
    items = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith('#EXTINF:'):
            if ',' in line:
                current = _u(line.split(',', 1)[1].strip())
            else:
                current = u'Канал'
        elif line.startswith('http://') or line.startswith('https://'):
            if current:
                items.append({'title': prefix + current, 'url': line})
                current = None
    return items

def local_candidates(filename):
    out = []
    for root in LOCAL_DIRS:
        out.append(os.path.join(root, filename))
    return out

def load_source(key, force):
    src = get_source(key)
    if not src:
        raise Exception(u'Источник не найден')
    cache = cache_path(key)
    title = src[1]
    remote = src[2]
    prefix = src[3]
    filename = src[4]
    errors = []
    if force or (not os.path.exists(cache)):
        try:
            text = fetch_url(remote)
            if '#EXTINF:' in text or '#EXTM3U' in text.upper():
                write_text(cache, text)
                return parse_m3u(text, prefix)
        except Exception as e:
            errors.append(_u(e))
            log_line(u'Ошибка загрузки ' + title + u': ' + _u(e))
    if os.path.exists(cache):
        text = safe_text(cache, u'')
        if text:
            return parse_m3u(text, prefix)
    for p in local_candidates(filename):
        if os.path.exists(p):
            text = safe_text(p, u'')
            if text:
                write_text(cache, text)
                return parse_m3u(text, prefix)
    raise Exception(u'Не найден плейлист: ' + title + (u'\n' + u'\n'.join(errors) if errors else u''))

def load_favs():
    data = read_json(FAV_FILE, [])
    return data if isinstance(data, list) else []

def save_favs(data):
    write_json(FAV_FILE, data)

def is_fav(url):
    for item in load_favs():
        if item.get('url') == url:
            return True
    return False

def add_fav(title, url, source):
    items = load_favs()
    for x in items:
        if x.get('url') == url:
            return False
    items.append({'title': title, 'url': url, 'source': source})
    save_favs(items)
    return True

def rem_fav(url):
    items = []
    for x in load_favs():
        if x.get('url') != url:
            items.append(x)
    save_favs(items)

def load_sites():
    data = read_json(SITE_FILE, None)
    if not isinstance(data, list):
        data = DEFAULT_SITES[:]
        write_json(SITE_FILE, data)
    return data

def save_sites(items):
    write_json(SITE_FILE, items)

def add_dir(label, query, plot):
    li = xbmcgui.ListItem(_u(label))
    try:
        li.setInfo('video', {'title': _u(label), 'plot': _u(plot)})
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, True)

def add_play(title, url, source):
    label = _u(title)
    if is_fav(url):
        label = u'★ ' + label
    li = xbmcgui.ListItem(label)
    try:
        li.setProperty('IsPlayable', 'true')
        li.setInfo('video', {'title': label, 'plot': u'Источник: ' + _u(source)})
    except Exception:
        pass
    menu = []
    if is_fav(url):
        menu.append((u'Убрать из избранного', 'RunPlugin(%s)' % build_url({'action':'fav_remove','url':url})))
    else:
        menu.append((u'Добавить в избранное', 'RunPlugin(%s)' % build_url({'action':'fav_add','title':title,'url':url,'source':source})))
    try:
        li.addContextMenuItems(menu, replaceItems=False)
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'play','title':title,'url':url}), li, False)

def show_root():
    add_dir(u'[B]Для Бати[/B] — Избранное', {'action':'favorites'}, u'Сохранённые каналы')
    add_dir(u'Украинские каналы', {'action':'source','key':'ua'}, u'Быстрый список')
    add_dir(u'Каналы на украинском', {'action':'source','key':'ukr'}, u'Список по языку')
    add_dir(u'Европейские каналы', {'action':'source','key':'eur'}, u'Европейский список')
    add_dir(u'Free-TV Украина', {'action':'source','key':'freeua'}, u'Дополнительный список')
    add_dir(u'Все каналы', {'action':'source','key':'all'}, u'Большой список, может открываться дольше')
    add_dir(u'Обновить плейлисты', {'action':'refresh_all'}, u'Загрузить и сохранить плейлисты')
    add_dir(u'Сайты для Бати', {'action':'sites'}, u'Сохранённые сайты и закладки')
    add_dir(u'Версия и обновление', {'action':'version'}, u'Версия плагина и проверка обновления')
    add_dir(u'Хвост логов', {'action':'logs'}, u'Последние сообщения плагина')
    add_dir(u'О программе', {'action':'about'}, u'Справка')
    xbmcplugin.endOfDirectory(HANDLE)

def show_source(key):
    src = get_source(key)
    if not src:
        xbmcgui.Dialog().ok(u'Для Бати', u'Источник не найден')
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    items = load_source(key, False)
    for item in items:
        add_play(item.get('title', u'Канал'), item.get('url', u''), src[1])
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(HANDLE)

def show_favs():
    items = load_favs()
    if not items:
        xbmcgui.Dialog().notification(u'Для Бати', u'Избранное пустое', xbmcgui.NOTIFICATION_INFO, 2500)
    for item in items:
        add_play(item.get('title',u'Канал'), item.get('url',u''), item.get('source',u'Избранное'))
    xbmcplugin.endOfDirectory(HANDLE)

def refresh_all():
    ok = 0
    errs = []
    for key, title, url, p, fn in SOURCES:
        try:
            load_source(key, True)
            ok += 1
        except Exception as e:
            errs.append(title + u': ' + _u(e))
    txt = u'Обновлено: %d из %d' % (ok, len(SOURCES))
    if errs:
        txt += u'\n\n' + u'\n'.join(errs[:5])
    xbmcgui.Dialog().ok(u'Для Бати', txt)
    xbmc.executebuiltin('Container.Refresh')

def parse_latest_version(xml_text):
    m = re.search(r'<addon\s+id="plugin\.video\.uaiptv"[^>]*version="([^"]+)"', xml_text)
    if m:
        return _u(m.group(1))
    return u''

def check_update():
    latest = u''
    err = u''
    try:
        xml_text = fetch_url(RAW_ADDONS_XML)
        latest = parse_latest_version(xml_text)
    except Exception as e:
        err = _u(e)
    return latest, err

def show_version():
    latest, err = check_update()
    lines = [u'Название: Для Бати', u'Текущая версия: ' + _u(ADDON_VERSION)]
    if latest:
        lines.append(u'Последняя версия в GitHub: ' + latest)
    if err:
        lines.append(u'Ошибка проверки обновления: ' + err)
    lines.append(u'Обновление выполняется через ZIP или репозиторий Kodi.')
    xbmcgui.Dialog().textviewer(u'Версия и обновление', u'\n'.join(lines))

def tail_log():
    if not os.path.exists(LOG_FILE):
        return u'Лог пока пуст.'
    text = safe_text(LOG_FILE, u'')
    arr = text.splitlines()
    if len(arr) > 120:
        arr = arr[-120:]
    return u'\n'.join(arr)

def show_logs():
    xbmcgui.Dialog().textviewer(u'Хвост логов', tail_log())

def show_about():
    text = u'Для Бати\n\n' \
           u'Упрощённый IPTV-плагин для старого Android 7 / Kodi 17.6.\n\n' \
           u'Возможности:\n' \
           u'• лёгкий стартовый экран\n' \
           u'• украинские и европейские списки\n' \
           u'• избранное\n' \
           u'• закладки сайтов\n' \
           u'• хвост логов\n' \
           u'• проверка версии\n\n' \
           u'Если онлайн-плейлисты не открываются, положите файлы .m3u в Download или на флешку.'
    xbmcgui.Dialog().textviewer(u'О программе', text)

def show_sites():
    add_dir(u'Открыть сохранённые сайты', {'action':'sites_list'}, u'Быстрый доступ к сайтам')
    add_dir(u'Добавить новый сайт', {'action':'site_add'}, u'Добавить адрес вручную')
    add_dir(u'Удалить сайт', {'action':'site_remove_select'}, u'Удалить из списка')
    xbmcplugin.endOfDirectory(HANDLE)

def show_sites_list():
    for item in load_sites():
        title = item.get('title', u'Сайт')
        url = item.get('url', u'')
        li = xbmcgui.ListItem(_u(title))
        try:
            li.setInfo('video', {'title': _u(title), 'plot': _u(url)})
            li.addContextMenuItems([(u'Удалить сайт', 'RunPlugin(%s)' % build_url({'action':'site_remove','url':url}))], replaceItems=False)
        except Exception:
            pass
        xbmcplugin.addDirectoryItem(HANDLE, build_url({'action':'site_open','url':url,'title':title}), li, False)
    xbmcplugin.endOfDirectory(HANDLE)

def site_add():
    kb1 = xbmc.Keyboard('', 'Название сайта')
    kb1.doModal()
    if not kb1.isConfirmed():
        return
    title = _u(kb1.getText()).strip()
    kb2 = xbmc.Keyboard('https://', 'Адрес сайта')
    kb2.doModal()
    if not kb2.isConfirmed():
        return
    url = _u(kb2.getText()).strip()
    if not title or not url:
        xbmcgui.Dialog().ok(u'Для Бати', u'Название и адрес обязательны')
        return
    items = load_sites()
    items.append({'title': title, 'url': url})
    save_sites(items)
    xbmcgui.Dialog().notification(u'Для Бати', u'Сайт сохранён', xbmcgui.NOTIFICATION_INFO, 2500)

def site_remove_select():
    items = load_sites()
    if not items:
        xbmcgui.Dialog().notification(u'Для Бати', u'Список сайтов пуст', xbmcgui.NOTIFICATION_INFO, 2500)
        return
    labels = []
    for item in items:
        labels.append(_u(item.get('title', u'Сайт')))
    idx = xbmcgui.Dialog().select(u'Удалить сайт', labels)
    if idx >= 0:
        del items[idx]
        save_sites(items)
        xbmcgui.Dialog().notification(u'Для Бати', u'Сайт удалён', xbmcgui.NOTIFICATION_INFO, 2500)

def site_remove(url):
    items = []
    for item in load_sites():
        if item.get('url') != url:
            items.append(item)
    save_sites(items)
    xbmcgui.Dialog().notification(u'Для Бати', u'Сайт удалён', xbmcgui.NOTIFICATION_INFO, 2500)
    xbmc.executebuiltin('Container.Refresh')

def site_open(title, url):
    try:
        xbmc.executebuiltin('StartAndroidActivity("", "android.intent.action.VIEW", "", "%s")' % _b(url))
        xbmcgui.Dialog().notification(u'Для Бати', u'Открываю сайт: ' + _u(title), xbmcgui.NOTIFICATION_INFO, 2000)
    except Exception:
        xbmcgui.Dialog().ok(u'Для Бати', u'Не удалось открыть сайт.\n' + _u(url))

def play_item(title, url):
    li = xbmcgui.ListItem(_u(title))
    try:
        li.setPath(_b(url))
    except Exception:
        pass
    xbmcplugin.setResolvedUrl(HANDLE, True, li)

def run():
    params = get_params()
    action = params.get('action', u'')
    if not action:
        show_root()
        return
    if action == u'source':
        show_source(params.get('key', u''))
    elif action == u'favorites':
        show_favs()
    elif action == u'play':
        play_item(params.get('title', u'Канал'), params.get('url', u''))
    elif action == u'fav_add':
        if add_fav(params.get('title', u'Канал'), params.get('url', u''), params.get('source', u'')):
            xbmcgui.Dialog().notification(u'Для Бати', u'Канал добавлен в избранное', xbmcgui.NOTIFICATION_INFO, 2500)
        else:
            xbmcgui.Dialog().notification(u'Для Бати', u'Канал уже в избранном', xbmcgui.NOTIFICATION_INFO, 2500)
    elif action == u'fav_remove':
        rem_fav(params.get('url', u''))
        xbmcgui.Dialog().notification(u'Для Бати', u'Канал удалён из избранного', xbmcgui.NOTIFICATION_INFO, 2500)
        xbmc.executebuiltin('Container.Refresh')
    elif action == u'refresh_all':
        refresh_all()
    elif action == u'version':
        show_version()
    elif action == u'logs':
        show_logs()
    elif action == u'about':
        show_about()
    elif action == u'sites':
        show_sites()
    elif action == u'sites_list':
        show_sites_list()
    elif action == u'site_add':
        site_add()
    elif action == u'site_remove_select':
        site_remove_select()
    elif action == u'site_remove':
        site_remove(params.get('url', u''))
    elif action == u'site_open':
        site_open(params.get('title', u'Сайт'), params.get('url', u''))
    else:
        show_root()

if __name__ == '__main__':
    try:
        log_line(u'Запуск плагина, версия ' + _u(ADDON_VERSION))
        run()
    except Exception as e:
        msg = _u(e)
        log_line(u'FATAL: ' + msg)
        try:
            xbmcgui.Dialog().ok(u'Ошибка Для Бати', u'Плагин не запустился.\n\n' + msg + u'\n\nОткройте раздел "Хвост логов" после следующего запуска.')
        except Exception:
            pass
