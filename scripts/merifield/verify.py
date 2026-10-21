#!/usr/bin/env python3
"""Check the integration points that can silently break a branded Android build."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET
r = Path(__file__).resolve().parents[2]
c = (r / 'CMakeLists.txt').read_text()
for setting, value in [('APP_NAME', 'Mérifield'), ('APP_ICON', 'merifield_logo'), ('APP_PACKAGE_NAME', 'merifield')]:
    assert f'set({setting} "{value}"' in c, setting
assert 'branding/merifield/theme.json' in c
source_theme = json.loads((r / 'resources/theme/theme.json').read_text())
custom_theme = json.loads((r / 'branding/merifield/theme.json').read_text())
for section, values in source_theme.items():
    assert set(values) == set(custom_theme[section]), section
for path in (r / 'platform/android/res/drawable').glob('*merifield*.xml'):
    ET.parse(path)
ns = '{http://schemas.android.com/apk/res/android}'
folder = r / 'platform/android/res/drawable'
for name in ['launcher_merifield_logo', 'merifield_logo_vector']:
    assert (folder / (name + '.xml')).is_file()
for path in folder.glob('*merifield*.xml'):
    for el in ET.parse(path).iter():
        for value in el.attrib.values():
            if value.startswith('@drawable/'):
                assert (folder / (value.split('/')[1] + '.xml')).is_file(), value
logo = ET.parse(r / 'branding/merifield/merifield_logo.svg')
assert len(logo.getroot()) >= 2
login = (r / 'src/app/qml/QfCloudLogin.qml').read_text()
for component in ['serverUrlLabel', 'serverUrlComboBox']:
    block = login.split('id: ' + component, 1)[1].split('\n    }', 1)[0]
    assert re.search(r'visible: cloudConnection.status === QfCloudConnection.Disconnected\s*\n', block), component
assert 'qrc:/images/app_logo.svg' in login
# The upstream service URL remains intact. No fictitious Mérifield server is configured.
assert 'return QStringLiteral( "https://app.qfield.cloud" )' in (r / 'src/core/qfieldcloud/qfcloudconnection.cpp').read_text()
assert (r / 'LICENSE').is_file()
print('Mérifield integration checks passed.')
