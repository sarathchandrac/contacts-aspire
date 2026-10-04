"""Creates a starter 'Analytics Overview' dashboard in Superset from the PostgreSQL analytics data.

Usage: python superset/create_dashboard.py   (Superset on http://localhost:8088)
Re-running reuses existing objects by name instead of duplicating them.
"""
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("SUPERSET_URL", "http://localhost:8088")
CFG = json.load(open(os.path.join(os.path.dirname(__file__), "..", "AppHost", "appsettings.Development.json")))["Parameters"]
DB_NAME = "Contacts & Analytics (PostgreSQL)"
DATASET = "analytics_enriched"
DASHBOARD = "Analytics Overview"

op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
headers = {}


def call(method, path, data=None):
    req = urllib.request.Request(BASE + path, method=method, headers={"Content-Type": "application/json", **headers},
                                 data=json.dumps(data).encode() if data is not None else None)
    try:
        with op.open(req) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:400]!r}")


def find(resource, col, value):
    q = urllib.parse.quote(f"(filters:!((col:{col},opr:eq,value:'{value}')))", safe="()!:,'")
    res = call("GET", f"/api/v1/{resource}/?q={q}")["result"]
    return res[0]["id"] if res else None


tok = call("POST", "/api/v1/security/login", {"username": "admin", "password": CFG["superset-admin-password"], "provider": "db"})
headers.update({"Authorization": "Bearer " + tok["access_token"], "Referer": BASE})
headers["X-CSRFToken"] = call("GET", "/api/v1/security/csrf_token/")["result"]

# --- dataset (virtual: events joined with users) ---
db_id = find("database", "database_name", DB_NAME)
ds_id = find("dataset", "table_name", DATASET)
if not ds_id:
    ds_id = call("POST", "/api/v1/dataset/", {
        "database": db_id, "schema": "public", "table_name": DATASET,
        "sql": "SELECT e.id, e.event_type, e.page, e.occurred_at, u.username, u.role "
               "FROM analytics_events e JOIN users u ON u.id = e.user_id",
    })["id"]
print("dataset", ds_id)

COUNT = {"expressionType": "SQL", "sqlExpression": "COUNT(*)", "label": "events", "optionName": "metric_events",
         "hasCustomLabel": True, "aggregate": None, "column": None}
DS = {"id": ds_id, "type": "table"}


def chart(name, viz_type, form_data, columns, orderby=None, row_limit=1000, extras=None):
    form_data = {"datasource": f"{ds_id}__table", "viz_type": viz_type, "metrics": [COUNT], "adhoc_filters": [],
                 "row_limit": row_limit, **form_data}
    query = {"columns": columns, "metrics": [COUNT], "orderby": orderby if orderby is not None else [],
             "row_limit": row_limit, "filters": [], "extras": extras or {"having": "", "where": ""},
             "annotation_layers": [], "series_limit": 0, "order_desc": True, "url_params": {}, "custom_params": {},
             "custom_form_data": {}}
    context = {"datasource": DS, "force": False, "queries": [query], "form_data": form_data,
               "result_format": "json", "result_type": "full"}
    return {"slice_name": name, "viz_type": viz_type, "datasource_id": ds_id, "datasource_type": "table",
            "params": json.dumps(form_data), "query_context": json.dumps(context)}


by_events = [[COUNT, False]]
charts = [
    chart("Total events", "big_number_total", {"metric": COUNT, "subheader": "events recorded", "y_axis_format": "SMART_NUMBER"}, []),
    chart("Events by type", "pie", {"groupby": ["event_type"], "metric": COUNT, "label_type": "key_value", "show_legend": True,
                                    "donut": True, "innerRadius": 40, "outerRadius": 70}, ["event_type"],
          orderby=by_events),
    chart("Events by page", "echarts_timeseries_bar", {"x_axis": "page", "groupby": [], "orientation": "vertical",
                                                       "x_axis_sort_asc": False, "x_axis_sort_series": "sum", "x_axis_sort_series_ascending": False,
                                                       "show_legend": False}, ["page"], orderby=by_events),
    chart("Top 5 users by activity", "echarts_timeseries_bar", {"x_axis": "username", "groupby": [], "orientation": "horizontal",
                                                                "show_legend": False, "row_limit": 5}, ["username"], orderby=by_events, row_limit=5),
    chart("Events per day", "echarts_timeseries_line", {"x_axis": "occurred_at", "time_grain_sqla": "P1D", "groupby": [],
                                                        "show_legend": False, "rich_tooltip": True},
          [{"timeGrain": "P1D", "columnType": "BASE_AXIS", "sqlExpression": "occurred_at", "label": "occurred_at", "expressionType": "SQL"}]),
]

dash_id = find("dashboard", "dashboard_title", DASHBOARD) or call("POST", "/api/v1/dashboard/", {"dashboard_title": DASHBOARD, "published": True})["id"]
chart_ids = []
for c in charts:
    cid = find("chart", "slice_name", c["slice_name"])
    c["dashboards"] = [dash_id]
    if cid:
        call("PUT", f"/api/v1/chart/{cid}", c)
    else:
        cid = call("POST", "/api/v1/chart/", c)["id"]
    chart_ids.append((cid, c["slice_name"]))
    print("chart", cid, c["slice_name"])

# --- layout: KPI + pie on top, bars in the middle, trend line at the bottom ---
def chart_node(cid, name, width, row, height=50):
    return {"type": "CHART", "id": f"CHART-{cid}", "children": [], "parents": ["ROOT_ID", "GRID_ID", row],
            "meta": {"width": width, "height": height, "chartId": cid, "sliceName": name}}

ids = dict((n, i) for i, n in chart_ids)
rows = [
    ("ROW-1", [("Total events", 4), ("Events by type", 8)]),
    ("ROW-2", [("Events by page", 6), ("Top 5 users by activity", 6)]),
    ("ROW-3", [("Events per day", 12)]),
]
layout = {
    "DASHBOARD_VERSION_KEY": "v2",
    "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
    "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [r for r, _ in rows], "parents": ["ROOT_ID"]},
    "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": DASHBOARD}},
}
for row_id, items in rows:
    layout[row_id] = {"type": "ROW", "id": row_id, "children": [f"CHART-{ids[n]}" for n, _ in items],
                      "parents": ["ROOT_ID", "GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"}}
    for n, w in items:
        layout[f"CHART-{ids[n]}"] = chart_node(ids[n], n, w, row_id)

call("PUT", f"/api/v1/dashboard/{dash_id}", {"position_json": json.dumps(layout), "published": True,
                                             "json_metadata": json.dumps({"refresh_frequency": 0, "color_scheme": ""})})
print(f"dashboard {dash_id}: {BASE}/superset/dashboard/{dash_id}/")
