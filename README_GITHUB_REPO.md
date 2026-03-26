# Alex-Doss/iptv — подготовка GitHub-репозитория с автообновлением Kodi-аддона

## Что внутри
- `repository/` — статический репозиторий Kodi, который нужно опубликовать в ветке `main`.
- `repository/zips/plugin.video.uaiptv/plugin.video.uaiptv-1.1.0.zip` — ZIP плагина.
- `repository/zips/repository.alexdoss.iptv/repository.alexdoss.iptv-1.0.0.zip` — ZIP репозитория, который ставится на приставку первым.
- `build_repository.py` — скрипт пересборки `addons.xml`, `addons.xml.md5` и ZIP-архивов после обновления версий.

## Как работает обновление
1. На приставку ставится `repository.alexdoss.iptv-1.0.0.zip`.
2. Kodi получает `addons.xml` и `addons.xml.md5` с GitHub Raw.
3. Когда версия `plugin.video.uaiptv` в `addon.xml` увеличивается, Kodi видит новую версию и предлагает/ставит обновление через Add-on Manager.
4. Это стандартный механизм репозиториев Kodi. Не надо делать самоустановку ZIP из кода плагина.

## Публикация в GitHub
1. Скопируй содержимое папки `repository/` в корень репозитория `https://github.com/Alex-Doss/iptv`.
2. Проверь, что после push доступны ссылки:
   - `https://raw.githubusercontent.com/Alex-Doss/iptv/main/repository/addons.xml`
   - `https://raw.githubusercontent.com/Alex-Doss/iptv/main/repository/addons.xml.md5`
   - `https://raw.githubusercontent.com/Alex-Doss/iptv/main/repository/zips/plugin.video.uaiptv/plugin.video.uaiptv-1.1.0.zip`
3. На приставке установи ZIP репозитория:
   `repository/zips/repository.alexdoss.iptv/repository.alexdoss.iptv-1.0.0.zip`
4. Затем установи из этого репозитория `UA IPTV`.

## Как выпускать следующую версию
1. Измени `version` в `repository/plugin.video.uaiptv/addon.xml`.
2. При необходимости обнови код `default.py`.
3. Запусти `python build_repository.py`.
4. Commit + push в GitHub.

## Ограничения
- На старом Kodi 17.6 автообновление зависит от настроек Add-ons → Updates.
- Некоторые потоки не откроются из-за старого SSL/кодеков/геоблоков.
- Автоматическая тихая переустановка «изнутри плагина» для Kodi 17.x — ненадёжный путь; репозиторий надёжнее.
