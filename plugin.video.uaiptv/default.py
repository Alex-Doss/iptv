# -*- coding: utf-8 -*-
import sys
import os
import re
import json
import time
import io
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
if not os.path.exists(PROFILE):
    os.makedirs(PROFILE)

HANDLE = int(sys.argv[1])
RAW_ADDONS_XML = 'https://raw.githubusercontent.com/Alex-Doss/iptv/main/repository/addons.xml'
LOCAL_DIRS = [
    '/storage/emulated/0/Download', '/sdcard/Download', '/mnt/sdcard/Download',
    '/storage/usbhost1', '/storage/usbhost0', '/mnt/usb_storage', '/mnt/usbhost1', '/mnt/usbhost0',
    '/storage/usbotg', '/mnt/media_rw/udisk'
]
SOURCES = [
    ('ua', u'Украинские каналы', 'https://iptv-org.github.io/iptv/countries/ua.m3u', u'[UA] ', 'ua.m3u'),
    ('ukr', u'Каналы на украинском', 'https://iptv-org.github.io/iptv/languages/ukr.m3u', u'[UA] ', 'ukr.m3u'),
    ('eur', u'Европейские каналы', 'https://iptv-org.github.io/iptv/regions/eur.m3u', u'[EU] ', 'eur.m3u'),
    ('freeua', u'Free-TV Украина', 'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlists/playlist_ukraine.m3u8', u'[UA] ', 'playlist_ukraine.m3u8'),
    ('all', u'Все каналы', 'https://iptv-org.github.io/iptv/index.m3u', u'', 'index.m3u')
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


def _u(value):
    try:
        if isinstance(value, unicode):
            return value
        return value.decode('utf-8')
    except Exception:
        try:
            return unicode(value, 'utf-8', 'ignore')
        except Exception:
            try:
                return unicode(str(value), 'utf-8', 'ignore')
            except Exception:
                return u''


def _s(value):
    try:
        if isinstance(value, unicode):
            return value.encode('utf-8')
        return str(value)
    except Exception:
        try:
            return unicode(value).encode('utf-8')
        except Exception:
            return ''


def log_line(message):
    text = _u(message)
    try:
        xbmc.log('[%s] %s' % (ADDON_ID, _s(text)), xbmc.LOGNOTICE)
    except Exception:
        pass
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    line = u'%s | %s
' % (_u(stamp), text)
    try:
        with io.open(LOG_FILE, 'a', encoding='utf-8') as fh:
            fh.write(line)
    except Exception:
        pass


def build_url(query):
    clean = {}
    for k, v in query.items():
        if isinstance(v, unicode):
            clean[k] = v.encode('utf-8')
        else:
            clean[k] = str(v)
    return sys.argv[0] + '?' + urllib.urlencode(clean)


def get_params():
    if len(sys.argv) < 3 or not sys.argv[2]:
        return {}
    query = sys.argv[2]
    if query.startswith('?'):
        query = query[1:]
    out = {}
    for chunk in query.split('&'):
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            out[k] = _u(urllib.unquote_plus(v))
    return out


def read_text(path, default=u''):
    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            return fh.read()
    except Exception:
        return default


def write_text(path, text):
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)
    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.write(_u(text))


def cache_path(key):
    return os.path.join(PROFILE, key + '.m3u')


def local_candidates(filename):
    out = []
    for root in LOCAL_DIRS:
        out.append(os.path.join(root, filename))
    return out


def fetch_url(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Batya IPTV)')
    req.add_header('Accept', '*/*')
    try:
        import ssl
        ctx = ssl._create_unverified_context()
        response = urllib2.urlopen(req, timeout=25, context=ctx)
    except Exception:
        response = urllib2.urlopen(req, timeout=25)
    data = response.read()
    try:
        return data.decode('utf-8')
    except Exception:
        try:
            return data.decode('utf-8', 'ignore')
        except Exception:
            return _u(data)


def get_source(key):
    for src in SOURCES:
        if src[0] == key:
            return src
    return None


def parse_m3u(data, prefix=u''):
    channels = []
    current_name = None
    current_group = u''
    for raw_line in data.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF:'):
            current_group = u''
            g = re.search(r'group-title="([^"]+)"', line)
            if g:
                current_group = _u(g.group(1))
            if ',' in line:
                current_name = _u(line.split(',', 1)[1].strip())
            else:
                current_name = u'Без названия'
        elif line.startswith('http://') or line.startswith('https://'):
            if current_name:
                title = prefix + current_name
                channels.append({'title': title, 'url': line, 'group': current_group})
                current_name = None
    return channels


def source_display_name(key):
    src = get_source(key)
    return src[1] if src else key


def load_source(key, force=False):
    src = get_source(key)
    if not src:
        raise Exception('Unknown source: ' + _s(key))
    _k, title, remote_url, prefix, local_name = src
    cp = cache_path(key)
    errors = []
    if force or not os.path.exists(cp):
        try:
            text = fetch_url(remote_url)
            if text and ('#EXTM3U' in text.upper() or '#EXTINF:' in text):
                write_text(cp, text)
                log_line(u'Обновлён плейлист: ' + title)
                return parse_m3u(text, prefix)
        except Exception as e:
            errors.append(u'REMOTE: ' + _u(e))
            log_line(u'Ошибка загрузки %s: %s' % (title, _u(e)))
    cached = read_text(cp)
    if cached:
        return parse_m3u(cached, prefix)
    for candidate in local_candidates(local_name):
        if os.path.exists(candidate):
            local_text = read_text(candidate)
            if local_text:
                write_text(cp, local_text)
                log_line(u'Взят локальный плейлист: ' + candidate)
                return parse_m3u(local_text, prefix)
    raise Exception(u'Не найден плейлист: ' + title + u'
' + u'
'.join(errors))


def load_favorites():
    try:
        raw = read_text(FAV_FILE, u'[]')
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_favorites(items):
    write_text(FAV_FILE, _u(json.dumps(items, ensure_ascii=False)))


def is_favorite(url):
    for item in load_favorites():
        if item.get('url') == url:
            return True
    return False


def add_favorite(title, url, source):
    items = load_favorites()
    for item in items:
        if item.get('url') == url:
            return False
    items.append({'title': title, 'url': url, 'source': source})
    save_favorites(items)
    log_line(u'Добавлено в избранное: ' + _u(title))
    return True


def remove_favorite(url):
    items = [x for x in load_favorites() if x.get('url') != url]
    save_favorites(items)
    log_line(u'Удалено из избранного: ' + _u(url))


def load_sites():
    text = read_text(SITE_FILE, u'')
    if not text:
        save_sites(DEFAULT_SITES)
        return list(DEFAULT_SITES)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    save_sites(DEFAULT_SITES)
    return list(DEFAULT_SITES)


def save_sites(items):
    write_text(SITE_FILE, _u(json.dumps(items, ensure_ascii=False)))


def add_site(title, url):
    items = load_sites()
    for item in items:
        if _u(item.get('url')) == _u(url):
            return False
    items.append({'title': _u(title), 'url': _u(url)})
    save_sites(items)
    log_line(u'Сайт добавлен: ' + _u(title) + u' -> ' + _u(url))
    return True


def remove_site(url):
    items = [x for x in load_sites() if _u(x.get('url')) != _u(url)]
    save_sites(items)
    log_line(u'Сайт удалён: ' + _u(url))


def add_dir_item(label, query, art=None, plot=None):
    li = xbmcgui.ListItem(_u(label))
    if art:
        try:
            li.setArt(art)
        except Exception:
            li.setIconImage(art.get('icon', ''))
            li.setThumbnailImage(art.get('thumb', ''))
    if plot:
        try:
            li.setInfo('video', {'plot': _u(plot), 'title': _u(label)})
        except Exception:
            pass
    xbmcplugin.addDirectoryItem(HANDLE, build_url(query), li, True)


def add_play_item(title, url, source):
    label = title
    if is_favorite(url):
        label = u'★ ' + _u(title)
    li = xbmcgui.ListItem(_u(label))
    try:
        li.setProperty('IsPlayable', 'true')
        li.setInfo('video', {'title': _u(title), 'plot': u'Источник: ' + _u(source)})
        li.setArt({'icon': 'DefaultVideo.png', 'thumb': 'DefaultVideo.png'})
    except Exception:
        pass
    if is_favorite(url):
        ctx = [(u'Убрать из избранного', 'RunPlugin(%s)' % build_url({'action': 'fav_remove', 'url': url, 'source': source}))]
    else:
        ctx = [(u'Добавить в избранное', 'RunPlugin(%s)' % build_url({'action': 'fav_add', 'title': title, 'url': url, 'source': source}))]
    try:
        li.addContextMenuItems(ctx, replaceItems=False)
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'play', 'title': title, 'url': url}), li, False)


def add_site_item(title, url):
    li = xbmcgui.ListItem(_u(title))
    try:
        li.setInfo('video', {'title': _u(title), 'plot': _u(url)})
        li.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
        li.addContextMenuItems([(u'Удалить сайт', 'RunPlugin(%s)' % build_url({'action': 'site_remove', 'url': url}))], replaceItems=False)
    except Exception:
        pass
    xbmcplugin.addDirectoryItem(HANDLE, build_url({'action': 'site_open', 'title': title, 'url': url}), li, False)


def tail_file(path, lines=80):
    if not os.path.exists(path):
        return u'Лог пока пуст.'
    text = read_text(path)
    arr = text.splitlines()
    if len(arr) > lines:
        arr = arr[-lines:]
    return u'
'.join(arr)


def parse_latest_version(xml_text):
    try:
        m = re.search(r'<addon\s+id="plugin\.video\.uaiptv"[^>]*version="([^"]+)"', xml_text)
        if m:
            return _u(m.group(1))
    except Exception:
        pass
    return u''


def version_tuple(v):
    out = []
    for chunk in _u(v).split('.'):
        try:
            out.append(int(chunk))
        except Exception:
            out.append(0)
    return tuple(out)


def check_update(force=False):
    now = int(time.time())
    state = {'last_check': 0, 'latest': u'', 'error': u''}
    try:
        state = json.loads(read_text(UPDATE_FILE, u'{"last_check": 0, "latest": "", "error": ""}'))
    except Exception:
        pass
    if (not force) and state.get('last_check') and now - int(state.get('last_check', 0)) < 3600 * 12:
        return state.get('latest', u''), state.get('error', u'')
    try:
        xml_text = fetch_url(RAW_ADDONS_XML)
        latest = parse_latest_version(xml_text)
        state = {'last_check': now, 'latest': latest, 'error': u''}
        write_text(UPDATE_FILE, _u(json.dumps(state, ensure_ascii=False)))
        return latest, u''
    except Exception as e:
        msg = _u(e)
        state = {'last_check': now, 'latest': state.get('latest', u''), 'error': msg}
        write_text(UPDATE_FILE, _u(json.dumps(state, ensure_ascii=False)))
        log_line(u'Ошибка проверки версии: ' + msg)
        return state.get('latest', u''), msg


def art_pack():
    icon = xbmc.translatePath(os.path.join(ADDON_PATH, 'icon.png'))
    fanart = xbmc.translatePath(os.path.join(ADDON_PATH, 'fanart.jpg'))
    return {'icon': icon, 'thumb': icon, 'fanart': fanart}


def show_root():
    art = art_pack()
    add_dir_item(u'[B]Для Бати[/B] — Избранное', {'action': 'favorites'}, art, u'Сохранённые каналы.')
    add_dir_item(u'Украинские каналы', {'action': 'source', 'key': 'ua'}, art, u'Основной быстрый список.')
    add_dir_item(u'Каналы на украинском', {'action': 'source', 'key': 'ukr'}, art, u'Список по языку.')
    add_dir_item(u'Европейские каналы', {'action': 'source', 'key': 'eur'}, art, u'Лёгкий европейский список.')
    add_dir_item(u'Free-TV Украина', {'action': 'source', 'key': 'freeua'}, art, u'Дополнительный украинский список.')
    add_dir_item(u'Все каналы', {'action': 'source', 'key': 'all'}, art, u'Большой общий список. Может открываться дольше.')
    add_dir_item(u'Сайты для Бати', {'action': 'sites'}, art, u'Список сохранённых сайтов и быстрый запуск.')
    add_dir_item(u'Обновить плейлисты', {'action': 'refresh_all'}, art, u'Скачать и сохранить плейлисты заново.')
    add_dir_item(u'Версия и обновление', {'action': 'version'}, art, u'Проверка версии в GitHub-репозитории.')
    add_dir_item(u'Хвост логов', {'action': 'logs'}, art, u'Последние сообщения и ошибки.')
    add_dir_item(u'О программе', {'action': 'about'}, art, u'Крупный простой интерфейс без лишней нагрузки.')
    xbmcplugin.setPluginCategory(HANDLE, _u(u'Для Бати'))
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def show_source(key):
    source_name = source_display_name(key)
    try:
        channels = load_source(key, False)
    except Exception as e:
        xbmcgui.Dialog().ok(u'Для Бати', _u(e))
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    for item in channels:
        add_play_item(item.get('title', u'Канал'), item.get('url', u''), source_name)
    xbmcplugin.setPluginCategory(HANDLE, source_name)
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(HANDLE)


def show_favorites():
    items = load_favorites()
    if not items:
        xbmcgui.Dialog().notification(u'Для Бати', u'Избранное пока пустое', xbmcgui.NOTIFICATION_INFO, 3000)
    for item in items:
        title = item.get('title', u'Канал')
        source = item.get('source', u'Избранное')
        add_play_item(title, item.get('url', u''), source)
    xbmcplugin.setPluginCategory(HANDLE, u'Избранное')
    xbmcplugin.setContent(HANDLE, 'videos')
    xbmcplugin.endOfDirectory(HANDLE)


def prompt_input(title, default=u''):
    kb = xbmc.Keyboard(_u(default), _u(title))
    kb.doModal()
    if kb.isConfirmed():
        return _u(kb.getText())
    return None


def show_sites():
    art = art_pack()
    add_dir_item(u'Добавить сайт', {'action': 'site_add'}, art, u'Введите название и адрес сайта.')
    add_dir_item(u'Как это работает', {'action': 'site_help'}, art, u'Открывает сайт во внешнем браузере Android.')
    sites = load_sites()
    for item in sites:
        add_site_item(item.get('title', u'Сайт'), item.get('url', u''))
    xbmcplugin.setPluginCategory(HANDLE, u'Сайты для Бати')
    xbmcplugin.endOfDirectory(HANDLE)


def site_help():
    text = u'Сайты открываются во внешнем браузере Android.

'            u'Если на боксе есть Chrome, Kodi попробует открыть ссылку там.
'            u'Если Chrome не сработает, будет попытка открыть системным браузером.

'            u'Сайт можно удалить через контекстное меню.'
    xbmcgui.Dialog().textviewer(u'Сайты для Бати', text)


def site_add():
    title = prompt_input(u'Название сайта', u'')
    if title is None or not title.strip():
        return
    url = prompt_input(u'Адрес сайта', u'https://')
    if url is None or not url.strip():
        return
    url = _u(url).strip()
    if not (url.startswith('http://') or url.startswith('https://')):
        url = u'https://' + url
    if add_site(title.strip(), url):
        xbmcgui.Dialog().notification(u'Для Бати', u'Сайт сохранён', xbmcgui.NOTIFICATION_INFO, 2500)
    else:
        xbmcgui.Dialog().notification(u'Для Бати', u'Такой сайт уже есть', xbmcgui.NOTIFICATION_INFO, 2500)
    xbmc.executebuiltin('Container.Refresh')


def site_open(title, url):
    safe_url = _u(url).replace(',', '%2C')
    commands = [
        'StartAndroidActivity(com.android.chrome,android.intent.action.VIEW,,%s)' % _s(safe_url),
        'StartAndroidActivity(com.android.browser,android.intent.action.VIEW,,%s)' % _s(safe_url),
        'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % _s(safe_url)
    ]
    for cmd in commands:
        try:
            xbmc.executebuiltin(cmd)
            log_line(u'Открытие сайта: ' + _u(url))
        except Exception as e:
            log_line(u'Ошибка открытия сайта: ' + _u(e))
    xbmcgui.Dialog().notification(u'Для Бати', u'Открываем сайт: ' + _u(title), xbmcgui.NOTIFICATION_INFO, 2500)


def refresh_all():
    ok = 0
    errors = []
    for key, title, _u1, _p, _f in SOURCES:
        try:
            load_source(key, True)
            ok += 1
        except Exception as e:
            errors.append(title + u': ' + _u(e))
    text = u'Обновлено: %d из %d' % (ok, len(SOURCES))
    if errors:
        text += u'

' + u'
'.join(errors[:5])
    xbmcgui.Dialog().ok(u'Для Бати', text)
    xbmc.executebuiltin('Container.Refresh')


def show_version():
    latest, err = check_update(True)
    lines = [u'Название: Для Бати', u'Текущая версия: ' + _u(ADDON_VERSION)]
    if latest:
        lines.append(u'Последняя версия в GitHub: ' + _u(latest))
        if version_tuple(latest) > version_tuple(ADDON_VERSION):
            lines.append(u'Статус: доступно обновление через репозиторий Kodi')
        else:
            lines.append(u'Статус: установлена актуальная версия')
    if err:
        lines.append(u'Ошибка проверки: ' + _u(err))
    lines.append(u'Источник обновления: GitHub / repository.addons.xml')
    xbmcgui.Dialog().textviewer(u'Версия и обновление', u'
'.join(lines))


def show_logs():
    xbmcgui.Dialog().textviewer(u'Хвост логов', tail_file(LOG_FILE, 120))


def show_about():
    text = u'Для Бати

'            u'Упрощённый IPTV-плагин для старого Android 7 / Kodi 17.6.

'            u'Что внутри:
'            u'• быстрый корневой экран без тяжёлой графики
'            u'• украинские и европейские списки
'            u'• избранное
'            u'• сохранённые сайты
'            u'• хвост логов
'            u'• раздел версии и обновления

'            u'Сайты открываются во внешнем браузере Android.'
    xbmcgui.Dialog().textviewer(u'О программе', text)


def play_item(title, url):
    li = xbmcgui.ListItem(_u(title))
    try:
        li.setPath(_s(url))
    except Exception:
        pass
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def run():
    params = get_params()
    action = params.get('action', u'')
    if not action:
        show_root()
    elif action == u'source':
        show_source(params.get('key', u''))
    elif action == u'favorites':
        show_favorites()
    elif action == u'play':
        play_item(params.get('title', u'Канал'), params.get('url', u''))
    elif action == u'fav_add':
        if add_favorite(params.get('title', u'Канал'), params.get('url', u''), params.get('source', u'')):
            xbmcgui.Dialog().notification(u'Для Бати', u'Канал добавлен в избранное', xbmcgui.NOTIFICATION_INFO, 2500)
        else:
            xbmcgui.Dialog().notification(u'Для Бати', u'Канал уже в избранном', xbmcgui.NOTIFICATION_INFO, 2500)
    elif action == u'fav_remove':
        remove_favorite(params.get('url', u''))
        xbmcgui.Dialog().notification(u'Для Бати', u'Канал удалён из избранного', xbmcgui.NOTIFICATION_INFO, 2500)
    elif action == u'sites':
        show_sites()
    elif action == u'site_help':
        site_help()
    elif action == u'site_add':
        site_add()
    elif action == u'site_open':
        site_open(params.get('title', u'Сайт'), params.get('url', u''))
    elif action == u'site_remove':
        remove_site(params.get('url', u''))
        xbmcgui.Dialog().notification(u'Для Бати', u'Сайт удалён', xbmcgui.NOTIFICATION_INFO, 2500)
        xbmc.executebuiltin('Container.Refresh')
    elif action == u'refresh_all':
        refresh_all()
    elif action == u'version':
        show_version()
    elif action == u'logs':
        show_logs()
    elif action == u'about':
        show_about()
    else:
        show_root()


if __name__ == '__main__':
    run()
