import importlib.util
import json
import os
import re
import shutil
import subprocess

import pytest

# spec/grafana is not a package, so load the build script by path. Importing it builds nothing.
_PATH = os.path.join(os.path.dirname(__file__), '..', 'spec', 'grafana', 'build_dashboard.py')
_SPEC = importlib.util.spec_from_file_location('build_dashboard', _PATH)
bd = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bd)

# Colour steps of the virtual battery cell, from ../kb/work/017-virtual-battery-kwh-display/spec.md section 2.
RED, ORANGE, YELLOW, GREEN, GREY = '#F2495C', '#FF9830', '#FADE2A', '#73BF69', '#8e8e8e'

needs_node = pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')


def vb_cell(prod, cons):
    """Run vbCell(prod, cons) from VB_JS in node and return its result."""
    script = bd.VB_JS + '\nprocess.stdout.write(JSON.stringify(vbCell(%s, %s)));' % (prod, cons)
    out = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10, check=True)
    return json.loads(out.stdout)


def _cez_blocks(query):
    return re.findall(r'from\(bucket: "default"\)\n  \|> range\(start: ([^)]*)\)\n'
                      r'  \|> filter\(fn: \(r\) => r._measurement == "cez"', query)


def test_panel80_query_reads_no_cez():
    assert '"cez"' not in bd.PANEL_80_QUERY_A
    assert 'vb_' not in bd.PANEL_80_QUERY_A


def test_panel81_query_reads_three_days():
    q = bd.PANEL_81_QUERY
    assert _cez_blocks(q) == ['-3d', '-3d']
    assert 'aggregated_production' in q and 'aggregated_consumption' in q
    assert 'vb_pct' not in q
    assert re.search(r'^  vb_prod: +vb_prod,$', q, re.M)
    assert re.search(r'^  vb_cons: +vb_cons,$', q, re.M)
    assert re.search(r'^vb_prod += .* else -1\.0$', q, re.M)
    assert re.search(r'^vb_cons += .* else -1\.0$', q, re.M)


def test_panel81_content_has_vb_cell():
    c = bd.PANEL_81_CONTENT
    assert 'data-vb-prod="{{vb_prod}}"' in c
    assert 'data-vb-cons="{{vb_cons}}"' in c
    assert 'id="estat-vb"' in c
    assert 'vb_pct' not in c
    assert re.search(r'\.estat \.val\.vb\{[^}]*white-space:nowrap', c)


def test_panel81_after_render_uses_vb_js():
    a = bd.PANEL_81_AFTER_RENDER
    assert bd.VB_JS in a
    assert 'getElementById("estat-vb")' in a
    assert 'dataset.vbProd' in a and 'dataset.vbCons' in a


def test_panel81_after_render_keeps_estat_bars():
    a = bd.PANEL_81_AFTER_RENDER
    assert 'setBars("estat-d-cons-bar","estat-d-prod-bar","estat-d-delta",dc,dg);' in a
    assert 'setBars("estat-m-cons-bar","estat-m-prod-bar","estat-m-delta",mc,mg);' in a


@needs_node
@pytest.mark.parametrize('prod,cons,colour', [
    (40, 100, RED),
    (50, 100, RED),
    (60, 100, ORANGE),
    (75, 100, YELLOW),
    (99, 100, YELLOW),
    (100, 100, GREEN),
    (150, 100, GREEN),
    (5, 0, GREEN),
    (0, 0, GREEN),
])
def test_vb_cell_colour_steps(prod, cons, colour):
    assert vb_cell(prod, cons)['color'] == colour


@needs_node
@pytest.mark.parametrize('prod,cons', [(-1, 100), (100, -1), (-1, -1), ('NaN', 100)])
def test_vb_cell_no_value(prod, cons):
    cell = vb_cell(prod, cons)
    assert cell == {'html': '—', 'color': GREY}


@needs_node
def test_vb_cell_text():
    html = vb_cell(3624, 2754)['html']
    text = re.sub(r'<[^>]+>', '', html)
    assert text == '3624 / 2754kWh'
    assert html.index('3624') < html.index(' / ') < html.index('2754') < html.index('kWh')
    assert re.sub(r'<[^>]+>', '', vb_cell(12345, 12345)['html']) == '12345 / 12345kWh'


# Change 021: panel 86, the Driving pill and the Charging rule.
def car_status(car, other, charge_w):
    """Run carStatus(car, other, chargeW) from CAR_STATUS_JS in node and return its result."""
    script = bd.CAR_STATUS_JS + '\nprocess.stdout.write(JSON.stringify(carStatus(%s, %s, %s)));' % (
        json.dumps(car), json.dumps(other), charge_w)
    out = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=10, check=True)
    return json.loads(out.stdout)


def _car(id, plug=0, time_left=0, driving=0, cap=100):
    return {'id': id, 'plug': plug, 'timeLeft': time_left, 'driving': driving, 'cap': cap}


def test_panel86_query_reads_driving():
    q = bd.PANEL_86_QUERY
    for car in ('enyaq', 'vw'):
        assert re.search(r'%s_driving_default = array\.from\(rows: \[\{_time: 2000-01-01T00:00:00Z, _value: 0\.0\}\]\)' % car, q)
        assert re.search(r'  \|> range\(start: -10m\)\n  \|> filter\(fn: \(r\) => r\._measurement == "Car" and '
                         r'r\._field == "driving_%s"\)' % car, q)
        assert re.search(r'^%s_driving = if exists %s_driving_rec\._value then float\(v: %s_driving_rec\._value\) '
                         r'else 0\.0$' % (car, car, car), q, re.M)
        assert '%s_driving: %s_driving' % (car, car) in q


def test_panel86_content_has_driving():
    c = bd.PANEL_86_CONTENT
    assert 'data-enyaq-driving="{{enyaq_driving}}"' in c
    assert 'data-vw-driving="{{vw_driving}}"' in c
    assert re.search(r'\.pill-car-drv\{[^}]*color:#5794F2', c)


def test_panel86_after_render_uses_car_status():
    a = bd.PANEL_86_AFTER_RENDER
    assert bd.CAR_STATUS_JS in a
    rest = a.replace(bd.CAR_STATUS_JS, '')
    assert rest.count('carStatus(') == 2
    assert 'dataset.enyaqDriving' in rest and 'dataset.vwDriving' in rest
    assert 'var enyaqCharging' not in a and 'var vwCharging' not in a


@needs_node
@pytest.mark.parametrize('car,other,charge_w,label', [
    (_car('enyaq', plug=1, time_left=30, driving=1), _car('vw'), 7000, 'Charging'),
    (_car('vw', plug=1, time_left=0), _car('enyaq'), 7090, 'Charging'),
    (_car('enyaq', driving=1), _car('vw'), 0, 'Driving'),
    (_car('enyaq', plug=1, driving=1), _car('vw'), 0, 'Driving'),
    (_car('enyaq', plug=1), _car('vw'), 0, 'Connected'),
    (_car('enyaq'), _car('vw'), 0, 'Disconnected'),
    (_car('vw', plug=1, time_left=30), _car('enyaq', plug=1), 7000, 'Charging'),
    (_car('enyaq', plug=1), _car('vw', plug=1, time_left=30), 7000, 'Connected'),
    (_car('vw', plug=1, cap=200), _car('enyaq', plug=1, cap=100), 7000, 'Charging'),
    (_car('enyaq', plug=1, cap=100), _car('vw', plug=1, cap=200), 7000, 'Connected'),
    (_car('enyaq', plug=1, cap=100), _car('vw', plug=1, cap=100), 7000, 'Charging'),
    (_car('vw', plug=1, cap=100), _car('enyaq', plug=1, cap=100), 7000, 'Connected'),
])
def test_car_status(car, other, charge_w, label):
    assert car_status(car, other, charge_w)['label'] == label

