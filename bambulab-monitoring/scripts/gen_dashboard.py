#!/usr/bin/env python3
"""Generate the P1S Grafana dashboard JSON (grafana/dashboards/p1s.json)."""
import json

DS = {"type": "prometheus", "uid": "prometheus"}
SEL = 'printer_name=~"$printer"'

# palette (dark-surface steps): blue, orange, aqua, yellow
C_BLUE, C_ORANGE, C_AQUA, C_YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
C_GOOD, C_WARN, C_CRIT = "green", "#c98500", "red"

_pid = 0
def pid():
    global _pid
    _pid += 1
    return _pid

def target(expr, legend="", instant=False, refid="A"):
    t = {"datasource": DS, "expr": expr, "refId": refid, "legendFormat": legend}
    if instant:
        t.update({"instant": True, "range": False})
    return t

def stat(title, targets, x, y, w=4, h=4, unit=None, text_mode="value",
         mappings=None, thresholds=None, no_value=None, decimals=None,
         color_mode="value", fixed_color=None):
    fc = {"mode": "thresholds"}
    if fixed_color:
        fc = {"mode": "fixed", "fixedColor": fixed_color}
    defaults = {
        "color": fc,
        "mappings": mappings or [],
        "thresholds": thresholds or {"mode": "absolute",
                                     "steps": [{"color": "text", "value": None}]},
    }
    if unit: defaults["unit"] = unit
    if no_value is not None: defaults["noValue"] = no_value
    if decimals is not None: defaults["decimals"] = decimals
    return {
        "id": pid(), "type": "stat", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": text_mode, "colorMode": color_mode,
            "graphMode": "none", "justifyMode": "auto", "orientation": "auto",
        },
    }

def gauge(title, targets, x, y, w=4, h=4, unit="percent", vmin=0, vmax=100,
          fixed_color=C_BLUE):
    return {
        "id": pid(), "type": "gauge", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": {
            "color": {"mode": "fixed", "fixedColor": fixed_color},
            "unit": unit, "min": vmin, "max": vmax, "decimals": 0,
            "thresholds": {"mode": "absolute",
                           "steps": [{"color": fixed_color, "value": None}]},
            "mappings": [],
        }, "overrides": []},
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "showThresholdLabels": False, "showThresholdMarkers": False,
        },
    }

def override_color(name, color, dash=False):
    props = [{"id": "color", "value": {"mode": "fixed", "fixedColor": color}}]
    if dash:
        props.append({"id": "custom.lineStyle",
                      "value": {"fill": "dash", "dash": [6, 6]}})
        props.append({"id": "custom.fillOpacity", "value": 0})
    return {"matcher": {"id": "byName", "options": name}, "properties": props}

def timeseries(title, targets, x, y, w=12, h=9, unit="celsius", vmin=None,
               vmax=None, overrides=None, legend=True, fixed_color=None):
    color = ({"mode": "fixed", "fixedColor": fixed_color}
             if fixed_color else {"mode": "palette-classic"})
    defaults = {
        "color": color, "unit": unit,
        "custom": {
            "drawStyle": "line", "lineWidth": 2, "fillOpacity": 8,
            "pointSize": 4, "showPoints": "never", "spanNulls": True,
            "gradientMode": "none",
            "axisGridShow": True,
        },
        "mappings": [],
        "thresholds": {"mode": "absolute",
                       "steps": [{"color": "text", "value": None}]},
    }
    if vmin is not None: defaults["min"] = vmin
    if vmax is not None: defaults["max"] = vmax
    return {
        "id": pid(), "type": "timeseries", "title": title, "datasource": DS,
        "gridPos": {"x": x, "y": y, "w": w, "h": h},
        "targets": targets,
        "fieldConfig": {"defaults": defaults, "overrides": overrides or []},
        "options": {
            "legend": {"showLegend": legend, "displayMode": "list",
                       "placement": "bottom",
                       "calcs": ["lastNotNull"] if legend else []},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
    }

def row(title, y):
    return {"id": pid(), "type": "row", "title": title, "collapsed": False,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1}, "panels": []}

panels = []

# ---- Row: Print status -----------------------------------------------------
panels.append(row("Print status", 0))
panels.append(stat(
    "State",
    [target(f'bambulab_printer_gcode_state{{{SEL}}} == 1', "{{state}}", instant=True)],
    0, 1, text_mode="name", no_value="Unknown"))
panels.append(stat(
    "Stage",
    [target(f'bambulab_print_stage_info{{{SEL}}} == 1', "{{stage}}", instant=True)],
    4, 1, text_mode="name", no_value="Unknown"))
panels.append(gauge(
    "Progress",
    [target(f'bambulab_print_progress_percent{{{SEL}}}')],
    8, 1))
panels.append(stat(
    "Time remaining",
    [target(f'bambulab_print_remaining_seconds{{{SEL}}}')],
    12, 1, unit="s", no_value="—"))
panels.append(stat(
    "Layer",
    [target(f'bambulab_print_layer_current{{{SEL}}}', "Current", refid="A"),
     target(f'bambulab_print_layer_total{{{SEL}}}', "Total", refid="B")],
    16, 1, decimals=0))
panels.append(stat(
    "Current job",
    [target(f'bambulab_subtask_name_info{{{SEL}}} == 1', "{{subtask_name}}",
            instant=True)],
    20, 1, text_mode="name", no_value="—"))

# ---- Row: Temperatures & fans ---------------------------------------------
panels.append(row("Temperatures & fans", 5))
panels.append(timeseries(
    "Temperatures",
    [target(f'bambulab_nozzle_temperature_celsius{{{SEL}}}', "Nozzle", refid="A"),
     target(f'bambulab_nozzle_target_temperature_celsius{{{SEL}}}', "Nozzle target", refid="B"),
     target(f'bambulab_bed_temperature_celsius{{{SEL}}}', "Bed", refid="C"),
     target(f'bambulab_bed_target_temperature_celsius{{{SEL}}}', "Bed target", refid="D"),
     target(f'bambulab_ams_unit_temperature_celsius{{{SEL}}}', "AMS", refid="E")],
    0, 6, vmin=0,
    overrides=[
        override_color("Nozzle", C_ORANGE),
        override_color("Nozzle target", C_ORANGE, dash=True),
        override_color("Bed", C_BLUE),
        override_color("Bed target", C_BLUE, dash=True),
        override_color("AMS", C_AQUA),
    ]))
panels.append(timeseries(
    "Fan speeds",
    [target(f'bambulab_fan_cooling_speed_percent{{{SEL}}}', "Part cooling", refid="A"),
     target(f'bambulab_fan_secondary_aux_speed_percent{{{SEL}}}', "Aux", refid="B"),
     target(f'bambulab_fan_big_1_speed_percent{{{SEL}}}', "Chamber 1", refid="C"),
     target(f'bambulab_fan_big_2_speed_percent{{{SEL}}}', "Chamber 2", refid="D"),
     target(f'bambulab_fan_heatbreak_speed_percent{{{SEL}}}', "Heatbreak", refid="E")],
    12, 6, unit="percent", vmin=0, vmax=100,
    overrides=[
        override_color("Part cooling", C_BLUE),
        override_color("Aux", C_ORANGE),
        override_color("Chamber 1", C_AQUA),
        override_color("Chamber 2", C_YELLOW),
        override_color("Heatbreak", "#d55181"),
    ]))

# ---- Row: AMS --------------------------------------------------------------
panels.append(row("AMS", 15))
panels.append(timeseries(
    "AMS humidity",
    [target(f'bambulab_ams_unit_humidity{{{SEL}}}', "AMS {{ams_id}}")],
    0, 16, w=8, h=8, unit="humidity", vmin=0, vmax=100,
    legend=False, fixed_color=C_BLUE))
panels.append(stat(
    "Humidity level (1 dry – 5 wet)",
    [target(f'bambulab_ams_unit_humidity_index{{{SEL}}}', "AMS {{ams_id}}")],
    8, 16, h=4, decimals=0,
    thresholds={"mode": "absolute", "steps": [
        {"color": C_GOOD, "value": None},
        {"color": C_WARN, "value": 3},
        {"color": C_CRIT, "value": 4}]}))
panels.append(stat(
    "Active slot",
    [target(f'max by (slot_id) (bambulab_ams_slot_active{{{SEL}}} == 1)',
            "Slot {{slot_id}}", instant=True, refid="A"),
     target(f'sum(bambulab_external_spool_active{{{SEL}}}) == 1',
            "External spool", instant=True, refid="B"),
     target(f'((sum(bambulab_ams_slot_active{{{SEL}}}) or vector(0))'
            f' + (sum(bambulab_external_spool_active{{{SEL}}}) or vector(0))) == 0',
            "None", instant=True, refid="C")],
    8, 20, h=4, text_mode="name", no_value="None"))
panels.append({
    "id": pid(), "type": "bargauge", "title": "Filament remaining", "datasource": DS,
    "gridPos": {"x": 12, "y": 16, "w": 8, "h": 8},
    "targets": [target(
        f'bambulab_ams_slot_remaining_percent{{{SEL}}}'
        ' * ignoring(tray_type, tray_color) group_left(tray_type, tray_color) '
        f'bambulab_ams_slot_tray_info{{{SEL}}}',
        "Slot {{slot_id}} · {{tray_type}}", instant=True)],
    "fieldConfig": {"defaults": {
        "color": {"mode": "fixed", "fixedColor": C_BLUE},
        "unit": "percent", "min": 0, "max": 100, "decimals": 0,
        "mappings": [{"type": "value", "options":
                      {"-1": {"text": "unknown", "index": 0}}}],
        "thresholds": {"mode": "absolute",
                       "steps": [{"color": C_BLUE, "value": None}]},
    }, "overrides": []},
    "options": {
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "orientation": "horizontal", "displayMode": "basic",
        "showUnfilled": True, "valueMode": "color",
    },
})

SPOOLS_TEMPLATE = """<div style="display:flex;flex-direction:column;gap:10px;padding:6px 4px">
{{#each data}}
<div style="display:flex;align-items:center;gap:10px">
  <span style="width:26px;height:26px;border-radius:50%;background:{{tray_color}};border:2px solid rgba(128,128,128,.45);flex:none"></span>
  <span>Slot {{slot_id}} &mdash; {{tray_type}}</span>
</div>
{{/each}}
</div>"""
panels.append({
    "id": pid(), "type": "marcusolsson-dynamictext-panel",
    "title": "Loaded filament", "datasource": DS,
    "gridPos": {"x": 20, "y": 16, "w": 4, "h": 8},
    "targets": [dict(target(
        f'bambulab_ams_slot_tray_info{{{SEL}}} == 1', instant=True),
        format="table")],
    "fieldConfig": {"defaults": {}, "overrides": []},
    "options": {
        "content": SPOOLS_TEMPLATE,
        "defaultContent": "No filament data.",
        "renderMode": "allRows",
        "editor": {"format": "auto", "language": "html"},
        "editors": [], "contentPartials": [], "externalStyles": [],
        "helpers": "", "styles": "", "afterRender": "", "wrap": True,
    },
})
# ---- Row: Health -----------------------------------------------------------
panels.append(row("Health", 24))
panels.append(stat(
    "Printer link",
    [target(f'bambulab_printer_connected{{{SEL}}}')],
    0, 25, w=6, text_mode="value",
    mappings=[{"type": "value", "options": {
        "1": {"text": "Connected", "color": C_GOOD, "index": 0},
        "0": {"text": "Disconnected", "color": C_CRIT, "index": 1}}}]))
panels.append(stat(
    "Print error code",
    [target(f'bambulab_print_error_code{{{SEL}}}')],
    6, 25, w=6, decimals=0,
    mappings=[{"type": "value", "options": {
        "0": {"text": "OK", "color": C_GOOD, "index": 0}}}],
    thresholds={"mode": "absolute", "steps": [
        {"color": C_CRIT, "value": None}, {"color": C_GOOD, "value": 0},
        {"color": C_CRIT, "value": 1}]}))
panels.append(stat(
    "Printer error code",
    [target(f'bambulab_printer_error_code{{{SEL}}}')],
    12, 25, w=6, decimals=0,
    mappings=[{"type": "value", "options": {
        "0": {"text": "OK", "color": C_GOOD, "index": 0}}}],
    thresholds={"mode": "absolute", "steps": [
        {"color": C_CRIT, "value": None}, {"color": C_GOOD, "value": 0},
        {"color": C_CRIT, "value": 1}]}))
panels.append(stat(
    "Data age",
    [target(f'time() - bambulab_exporter_last_success_unixtime{{{SEL}}}')],
    18, 25, w=6, unit="s", decimals=0,
    thresholds={"mode": "absolute", "steps": [
        {"color": C_GOOD, "value": None},
        {"color": C_WARN, "value": 60},
        {"color": C_CRIT, "value": 300}]}))

panels.append({
    "id": pid(), "type": "alertlist", "title": "Alerts",
    "gridPos": {"x": 0, "y": 29, "w": 24, "h": 5},
    "options": {
        "alertName": "", "dashboardAlerts": False,
        "groupBy": [], "groupMode": "default", "maxItems": 20,
        "sortOrder": 1, "viewMode": "list",
        "stateFilter": {"firing": True, "pending": True, "recovering": True,
                        "noData": True, "normal": True, "error": True},
        "folder": None,
    },
})

dashboard = {
    "uid": "bambu-p1s",
    "title": "P1S Printer",
    "tags": ["bambulab", "3d-printing"],
    "timezone": "browser",
    "schemaVersion": 39,
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "editable": True,
    "templating": {"list": [{
        "name": "printer",
        "label": "Printer",
        "type": "query",
        "datasource": DS,
        "query": {"qryType": 1,
                  "query": "label_values(bambulab_printer_up, printer_name)",
                  "refId": "var-printer"},
        "refresh": 2,
        "includeAll": False, "multi": False,
        "current": {"text": "P1S", "value": "P1S"},
        "options": [], "sort": 1,
    }]},
    "panels": panels,
}

out = "dashboards/p1s.json"
with open(out, "w") as f:
    json.dump(dashboard, f, indent=2)
print(f"wrote {out}: {len(panels)} panels")
