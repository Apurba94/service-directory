"""The offline web app."""
import json
from datetime import date, datetime

from . import core
from .fieldkit import App, Fail, card, form, h, redirect, stats, table

SCHEMA = "CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, needs TEXT NOT NULL, area TEXT NOT NULL DEFAULT '', lat REAL, lon REAL, languages TEXT NOT NULL, hours TEXT NOT NULL DEFAULT '', free INTEGER NOT NULL DEFAULT 1, groups TEXT NOT NULL DEFAULT '[]', contact TEXT NOT NULL DEFAULT '', verified TEXT NOT NULL DEFAULT '');"
NEEDS = ["health", "food", "shelter", "legal", "education", "protection", "mental health", "water", "livelihoods"]


def split(text):
    return [x.strip() for x in text.split(",") if x.strip()]


def create_app(db="services.db", clock=datetime.now):
    a = App("Service Directory", db, SCHEMA, [("Find help", "/"), ("Add a service", "/add"), ("Gaps", "/gaps")])

    def services():
        return [core.Service(r["id"], r["name"], tuple(json.loads(r["needs"])), r["area"], r["lat"], r["lon"], tuple(json.loads(r["languages"])), r["hours"], bool(r["free"]), tuple(json.loads(r["groups"])), r["verified"]) for r in a.rows("SELECT * FROM services ORDER BY name")]

    def areas():
        return [r["area"] for r in a.rows("SELECT DISTINCT area FROM services WHERE area != '' ORDER BY area")]

    @a.route("/", ("GET",))
    def home(req):
        need = req.get("need")
        result = ""
        if need:
            hits = core.match(services(), need, language=req.get("language") or None, group=req.get("group") or None, when=clock(), free_only=bool(req.get("free")), area=req.get("area") or None)
            contact = {r["id"]: r["contact"] for r in a.rows("SELECT id, contact FROM services")}
            result = card(f"Services for {need}", table(hits, [("Service", lambda x: x[1].name), ("Why", lambda x: ", ".join(x[3])), ("Hours", lambda x: x[1].hours), ("Contact", lambda x: contact[x[1].id])], "Nothing is listed for this need. Check the Gaps page."))
        options = "".join(f'<option value="{h(n)}"{" selected" if n == need else ""}>{h(n)}</option>' for n in NEEDS)
        area_opts = '<option value=""></option>' + "".join(f'<option value="{h(x)}">{h(x)}</option>' for x in areas())
        search = f'<form method="get" action="/"><label>What is needed?<select name="need">{options}</select></label><label>Area<select name="area">{area_opts}</select></label><label>Language<select name="language"><option value="">Any</option><option value="bn">Bangla</option><option value="en">English</option><option value="rhg">Rohingya</option></select></label><label>For<select name="group"><option value="">Anyone</option><option value="women">Women</option><option value="children">Children</option><option value="disability">People with disabilities</option></select></label><button>Search</button></form>'
        return a.page("Find help", stats([("Services", a.one("SELECT COUNT(*) FROM services"))]) + card("Search", search) + result)

    @a.route("/add", ("GET", "POST"))
    def add(req):
        if req.method == "POST":
            hours = req.text("hours", False)
            try:
                core.parse_hours(hours)
            except ValueError as exc:
                raise Fail(str(exc)) from None
            needs = split(req.text("needs"))
            if not needs:
                raise Fail("List at least one need")
            lat = req.number("lat", low=-90, high=90) if str(req.get("lat")).strip() else None
            lon = req.number("lon", low=-180, high=180) if str(req.get("lon")).strip() else None
            a.run("INSERT INTO services (name, needs, area, lat, lon, languages, hours, free, groups, contact, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", req.text("name"), json.dumps(needs), req.text("area", False), lat, lon, json.dumps(split(req.text("languages", False)) or ["bn"]), hours, 0 if req.get("paid") else 1, json.dumps(split(req.text("groups", False))), req.text("contact", False), clock().date().isoformat())
            return redirect("/")
        return a.page("Add a service", card("Service", form(a, "/add", [("name", "Name"), ("needs", "Needs met, separated by commas: " + ", ".join(NEEDS)), ("area", "Area"), ("lat", "Latitude", "number"), ("lon", "Longitude", "number"), ("languages", "Language codes, such as bn, en, rhg"), ("hours", "Hours, such as Sun-Thu 09:00-17:00; Sat 10:00-13:00"), ("groups", "Only serves, such as women, children (blank for everyone)"), ("contact", "Contact desk or public phone"), ("paid", "Charges a fee", "checkbox", "1")], "Add")))

    @a.route("/gaps")
    def gaps(req):
        s = services()
        return a.page("Gaps", card("Needs with no service in an area", table(core.gaps(s, NEEDS, areas()), [("Need", lambda r: r[0]), ("Area", lambda r: r[1])], "Every need has a service in each listed area.")) + card("Needs with only one provider", table(core.single_points(s, NEEDS), [("Need", lambda r: r[0]), ("Provider", lambda r: r[1])], "None.")) + card("Details to check again", table(core.stale(s, clock().date()), [("Service", lambda r: r[0].name), ("Days since checked", lambda r: "never" if r[1] is None else r[1])], "All details are recent.")))

    return a
