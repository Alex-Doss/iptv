import os, zipfile, hashlib, re, shutil
ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(ROOT, 'repository')
ZIPS = os.path.join(REPO, 'zips')

ADDONS = [
    ('plugin.video.uaiptv', os.path.join(REPO, 'plugin.video.uaiptv')),
    ('repository.alexdoss.iptv', os.path.join(REPO, 'repository.alexdoss.iptv')),
]


def version_from_xml(path):
    data = open(path, 'r').read()
    m = re.search(r'version="([^"]+)"', data)
    if not m:
        raise RuntimeError('Version not found in %s' % path)
    return m.group(1), data


def zip_addon(addon_id, src_dir, version):
    out_dir = os.path.join(ZIPS, addon_id)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    zip_path = os.path.join(out_dir, '%s-%s.zip' % (addon_id, version))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src_dir):
            for name in files:
                ap = os.path.join(root, name)
                rel = os.path.relpath(ap, src_dir)
                zf.write(ap, os.path.join(addon_id, rel))
    return zip_path


def main():
    xml_parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    for addon_id, src_dir in ADDONS:
        version, xml = version_from_xml(os.path.join(src_dir, 'addon.xml'))
        zip_addon(addon_id, src_dir, version)
        xml_parts.append(xml)
    addons_xml = '
'.join(xml_parts) + '
'
    open(os.path.join(REPO, 'addons.xml'), 'w').write(addons_xml)
    open(os.path.join(REPO, 'addons.xml.md5'), 'w').write(hashlib.md5(addons_xml.encode('utf-8')).hexdigest())
    print('Repository rebuilt successfully.')

if __name__ == '__main__':
    main()
