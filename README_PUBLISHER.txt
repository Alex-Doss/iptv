README_PUBLISHER.txt

Этот архив подготовлен для инструмента github_publisher_rewritten_v4.py.

Структура внутри:
- repository/
  - plugin.video.uaiptv/
  - repository.alexdoss.iptv/
  - zips/
  - addons.xml
  - addons.xml.md5

Как использовать:
1. В инструменте выберите этот ZIP как "готовый архив проекта".
2. Включите режим обновления Kodi repository, если публикуете новую версию.
3. Для обновления самого IPTV-плагина инструмент должен:
   - изменить version в repository/plugin.video.uaiptv/addon.xml
   - собрать новый ZIP в repository/zips/plugin.video.uaiptv/
   - пересобрать repository/addons.xml
   - пересчитать repository/addons.xml.md5
4. После этого выполнить commit/push в GitHub.

Важно:
- Это архив для публикации в GitHub, не для прямой установки на TV box.
- Для TV box используйте отдельный install ZIP самого add-on или repository add-on.
