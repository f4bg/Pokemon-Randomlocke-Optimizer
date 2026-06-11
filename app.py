import csv
import os
import json
from flask import Flask, jsonify, request, render_template, send_from_directory
import requests

app = Flask(__name__)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CAUGHT_FILE = os.path.join(DATA_DIR, "caught.json")
ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
SAVES_DIR = os.path.join(DATA_DIR, "saves")
os.makedirs(SAVES_DIR, exist_ok=True)

pokemon_data = {}
evolution_map = {}
item_catalog = {}

def load_pokemon():
    path = os.path.join(DATA_DIR, "Pokemon.csv")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"]
            form = row.get("Form", "").strip()
            key = f"{name} {form}" if form and form != " " else name
            if name == "Nidoran" and "Female" in form:
                name = "Nidoran\u2640"
                key = name
            elif name == "Nidoran" and "Male" in form:
                name = "Nidoran\u2642"
                key = name
            pokemon_data[key] = {
                "id": int(row["ID"]),
                "name": name,
                "form": form,
                "type1": row["Type1"],
                "type2": row["Type2"],
                "total": int(row["Total"]),
                "hp": int(row["HP"]),
                "attack": int(row["Attack"]),
                "defense": int(row["Defense"]),
                "sp_atk": int(row["Sp. Atk"]),
                "sp_def": int(row["Sp. Def"]),
                "speed": int(row["Speed"]),
                "generation": int(row["Generation"]),
            }

def load_evolutions():
    path = os.path.join(DATA_DIR, "pokemon_evoluciones.csv")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pre = row["pokemon"].strip().lower()
            form = row.get("form", "").strip().lower()
            key = (pre, form)
            if key not in evolution_map:
                evolution_map[key] = []
            evolution_map[key].append(row)

def load_item_catalog():
    path = os.path.join(DATA_DIR, "items.csv")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nombre = row["nombre"].strip()
            valor = row["valor"].strip()
            item_catalog[valor.upper()] = nombre

def _norm(s):
    return s.lower().strip().replace("-", "").replace("'", "").replace(".", "").replace(" ", "")

def get_name_key(name):
    name_norm = _norm(name)
    for key in pokemon_data:
        if _norm(key) == name_norm:
            return key
    for key in pokemon_data:
        if _norm(pokemon_data[key]["name"]) == name_norm:
            return key
    return None

def build_sprite_name(name, form=""):
    base = name.lower().replace(' ', '-').replace('.', '').replace('\u2640', '-f').replace('\u2642', '-m')
    f = form.strip() if form else ""
    if not f or f == " ":
        return base
    f_lower = f.lower()
    if f_lower.startswith("alolan "):
        return f"{base}-alola"
    if f_lower.startswith("galarian "):
        return f"{base}-galar"
    if f_lower.startswith("hisuian "):
        return f"{base}-hisui"
    return base

def is_regional_form(form):
    f = form.strip().lower() if form else ""
    return f.startswith("alolan ") or f.startswith("galarian ") or f.startswith("hisuian ")

def find_pokemon_by_base_name(base_name):
    base_norm = _norm(base_name)
    if "nidoran" in base_norm:
        if "female" in base_norm or "\u2640" in base_norm:
            return get_name_key("Nidoran\u2640")
        if "male" in base_norm or "\u2642" in base_norm:
            return get_name_key("Nidoran\u2642")
    for key, data in pokemon_data.items():
        if _norm(data["name"]) == base_norm and (not data["form"] or data["form"] == " "):
            return key
    for key, data in pokemon_data.items():
        if _norm(data["name"]) == base_norm:
            return key
    return None

def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def migrate_items(items):
    result = []
    for item in items:
        if isinstance(item, str):
            result.append({"name": item.upper(), "stock": 1})
        elif isinstance(item, dict):
            result.append({"name": item.get("name", "").upper(), "stock": item.get("stock", 1)})
    return result

def get_owned_item_names():
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    return [i["name"] for i in items]

def has_item_stock(item_name):
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    item_name = item_name.upper()
    for i in items:
        if i["name"] == item_name:
            return i["stock"]
    return 0

def consume_item(item_name):
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    item_name = item_name.upper()
    for i, item in enumerate(items):
        if item["name"] == item_name:
            if item["stock"] > 1:
                items[i]["stock"] -= 1
            else:
                items.pop(i)
            save_json(ITEMS_FILE, items)
            return True
    save_json(ITEMS_FILE, items)
    return False

def item_stock_str(item):
    return f"{item['name']} x{item['stock']}"

load_pokemon()
load_evolutions()
load_item_catalog()

def load_type_chart():
    path = os.path.join(DATA_DIR, "Pokemon Type Chart.csv")
    chart = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        types = [h.strip() for h in headers[1:] if h.strip()]
        for row in reader:
            attacking = row[0].strip()
            chart[attacking] = {}
            for i, val in enumerate(row[1:]):
                if i < len(types):
                    chart[attacking][types[i]] = float(val)
    return chart, types

type_chart, all_types = load_type_chart()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/pokemon")
def api_pokemon():
    q = request.args.get("q", "").lower()
    if q:
        results = []
        for key, data in pokemon_data.items():
            if q in key.lower() or q in data["name"].lower():
                results.append(data)
        return jsonify(results)
    return jsonify(list(pokemon_data.values()))

@app.route("/api/suggestions")
def api_suggestions():
    q = request.args.get("q", "").lower()
    if len(q) < 1:
        return jsonify([])
    regional_map = {}
    for key, data in pokemon_data.items():
        n = data["name"]
        form = data.get("form", "")
        if n not in regional_map:
            regional_map[n] = False
        if is_regional_form(form):
            regional_map[n] = True
    results = []
    seen = set()
    for key, data in pokemon_data.items():
        display = data["name"]
        if display not in seen:
            if q in display.lower():
                results.append({"name": display, "form": data.get("form", ""), "total": data["total"], "has_regional_forms": regional_map.get(display, False)})
                seen.add(display)
    caught = get_caught_names_lower()
    for r in results:
        r["caught"] = r["name"].lower() in caught
    return jsonify(sorted(results, key=lambda x: x["total"], reverse=True)[:20])

def get_caught():
    return load_json(CAUGHT_FILE, [])

def get_caught_names_lower():
    return [c["name"].lower() for c in get_caught()]

@app.route("/api/caught", methods=["GET"])
def api_get_caught():
    caught = get_caught()
    enriched = []
    for c in caught:
        name = c["name"]
        form = c.get("form", "").strip()
        key = None
        if form:
            for k, v in pokemon_data.items():
                if v["name"].lower() == name.lower() and v.get("form", "").strip().lower() == form.lower():
                    key = k
                    break
        if not key:
            key = get_name_key(name)
        stats = pokemon_data.get(key, {})
        enriched.append({**c, "stats": stats})
    enriched.reverse()
    return jsonify(enriched)

@app.route("/api/caught", methods=["POST"])
def api_add_caught():
    data = request.json
    name = data.get("name", "").strip()
    form = data.get("form", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    if form:
        key = None
        for k, v in pokemon_data.items():
            if v["name"].lower() == name.lower() and v.get("form", "").strip().lower() == form.lower():
                key = k
                break
        if not key:
            return jsonify({"error": f"Pokemon '{name}' form '{form}' not found"}), 404
    else:
        key = get_name_key(name)
        if not key:
            return jsonify({"error": f"Pokemon '{name}' not found"}), 404
    caught = get_caught()
    nick = data.get("nickname", pokemon_data[key]["name"])
    level = data.get("level", 1)
    already = [c for c in caught if c["name"].lower() == pokemon_data[key]["name"].lower()]
    entry = {
        "name": pokemon_data[key]["name"],
        "form": pokemon_data[key].get("form", ""),
        "nickname": nick,
        "level": level,
    }
    if already:
        caught[caught.index(already[0])] = entry
    else:
        caught.append(entry)
    save_json(CAUGHT_FILE, caught)
    stats = pokemon_data[key]
    highlights = get_highlights(stats)
    return jsonify({"caught": entry, "stats": stats, "highlights": highlights})

@app.route("/api/caught/clear", methods=["DELETE"])
def api_clear_caught():
    save_json(CAUGHT_FILE, [])
    return jsonify({"success": True})

@app.route("/api/caught/<name>", methods=["DELETE"])
def api_delete_caught(name):
    caught = get_caught()
    caught = [c for c in caught if c["name"].lower() != name.lower()]
    save_json(CAUGHT_FILE, caught)
    return jsonify({"success": True})

@app.route("/api/new-game", methods=["POST"])
def api_new_game():
    import shutil, datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = {}
    for fname, label in [(CAUGHT_FILE, "caught"), (ITEMS_FILE, "items"), (CONFIG_FILE, "config")]:
        if os.path.exists(fname):
            backup_file = os.path.join(SAVES_DIR, f"{label}_{ts}.json")
            shutil.copy2(fname, backup_file)
            saved[label] = backup_file
    save_json(CAUGHT_FILE, [])
    save_json(ITEMS_FILE, [])
    save_json(CONFIG_FILE, {"level_cap": 14})
    return jsonify({"success": True, "backup_ts": ts})

@app.route("/api/backups")
def api_list_backups():
    import re, json as j
    name_index_path = os.path.join(SAVES_DIR, "_names.json")
    name_map = {}
    if os.path.exists(name_index_path):
        try:
            name_map = j.load(open(name_index_path, "r"))
        except:
            name_map = {}
    files = os.listdir(SAVES_DIR)
    groups = {}
    for f in files:
        m = re.match(r"(caught|items|config)(?:_backup)?_(\d{8}_\d{6})\.json", f)
        if m:
            ts = m.group(2)
            if ts not in groups:
                groups[ts] = {"ts": ts, "files": {}}
            groups[ts]["files"][m.group(1)] = f
    backups = sorted(groups.values(), key=lambda x: x["ts"], reverse=True)
    result = []
    for b in backups:
        has_all = all(k in b["files"] for k in ("caught", "items", "config"))
        entry = {
            "timestamp": b["ts"],
            "complete": has_all,
            "files": b["files"]
        }
        if b["ts"] in name_map:
            entry["name"] = name_map[b["ts"]]
        result.append(entry)
    return jsonify(result)

@app.route("/api/backups/save", methods=["POST"])
def api_save_backup():
    import shutil, datetime, json as j
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    safe_name = name.replace(" ", "_")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name_index_path = os.path.join(SAVES_DIR, "_names.json")
    name_map = {}
    if os.path.exists(name_index_path):
        try:
            name_map = j.load(open(name_index_path, "r"))
        except:
            name_map = {}
    name_map[ts] = name
    with open(name_index_path, "w") as f:
        j.dump(name_map, f, indent=2)
    for fname, label in [(CAUGHT_FILE, "caught"), (ITEMS_FILE, "items"), (CONFIG_FILE, "config")]:
        if os.path.exists(fname):
            backup_file = os.path.join(SAVES_DIR, f"{label}_{ts}.json")
            shutil.copy2(fname, backup_file)
    return jsonify({"success": True, "timestamp": ts, "name": name})

@app.route("/api/backups/delete", methods=["POST"])
def api_delete_backup():
    import json as j
    ts = request.json.get("timestamp", "")
    if not ts:
        return jsonify({"error": "Missing timestamp"}), 400
    for label in ("caught", "items", "config"):
        for prefix in ("", "_backup"):
            path = os.path.join(SAVES_DIR, f"{label}{prefix}_{ts}.json")
            if os.path.exists(path):
                os.remove(path)
    name_index_path = os.path.join(SAVES_DIR, "_names.json")
    if os.path.exists(name_index_path):
        try:
            name_map = j.load(open(name_index_path, "r"))
            if ts in name_map:
                del name_map[ts]
                with open(name_index_path, "w") as f:
                    j.dump(name_map, f, indent=2)
        except:
            pass
    return jsonify({"success": True})

@app.route("/api/backups/restore", methods=["POST"])
def api_restore_backup():
    import shutil
    ts = request.json.get("timestamp", "")
    if not ts:
        return jsonify({"error": "Missing timestamp"}), 400
    restored = {}
    for label in ("caught", "items", "config"):
        src = os.path.join(SAVES_DIR, f"{label}_{ts}.json")
        src_old = os.path.join(SAVES_DIR, f"{label}_backup_{ts}.json")
        path = src if os.path.exists(src) else (src_old if os.path.exists(src_old) else None)
        if path:
            dst = os.path.join(DATA_DIR, f"{label}.json")
            shutil.copy2(path, dst)
            restored[label] = True
    return jsonify({"success": True, "restored": restored})

def get_highlights(stats):
    highlights = []
    if not stats:
        return highlights
    for stat_name, col in [("HP", "hp"), ("Attack", "attack"), ("Defense", "defense"),
                           ("Sp. Atk", "sp_atk"), ("Sp. Def", "sp_def"), ("Speed", "speed"),
                           ("Total", "total")]:
        val = stats[col]
        is_best = all(val >= p[col] for p in pokemon_data.values())
        if is_best:
            highlights.append(f"Highest {stat_name} of all Pokemon!")
    return highlights

@app.route("/api/team/best")
def api_best_team():
    caught = get_caught()
    if not caught:
        return jsonify([])
    enriched = []
    for c in caught:
        key = get_name_key(c["name"])
        stats = pokemon_data.get(key, {})
        if stats:
            enriched.append({**c, "stats": stats, "total": stats.get("total", 0)})
    enriched.sort(key=lambda x: x["total"], reverse=True)
    return jsonify(enriched[:6])

@app.route("/api/team/best-stat")
def api_best_stat():
    stat = request.args.get("stat", "total")
    stat_map = {
        "hp": "hp", "attack": "attack", "defense": "defense",
        "sp_atk": "sp_atk", "sp_def": "sp_def", "speed": "speed", "total": "total"
    }
    col = stat_map.get(stat, "total")
    caught = get_caught()
    enriched = []
    for c in caught:
        key = get_name_key(c["name"])
        stats = pokemon_data.get(key, {})
        if stats:
            enriched.append({**c, "stats": stats, "value": stats.get(col, 0)})
    enriched.sort(key=lambda x: x["value"], reverse=True)
    return jsonify(enriched)

@app.route("/api/level-cap", methods=["GET", "POST"])
def api_level_cap():
    config = load_json(CONFIG_FILE, {"level_cap": 14})
    if request.method == "POST":
        config["level_cap"] = request.json.get("level_cap", 14)
        save_json(CONFIG_FILE, config)
    return jsonify(config)

@app.route("/api/evolutions/available")
def api_available_evolutions():
    caught = get_caught()
    config = load_json(CONFIG_FILE, {"level_cap": 14})
    items_owned = get_owned_item_names()
    level_cap = config["level_cap"]
    available = []

    for c in caught:
        name_lower = c["name"].lower()
        form = c.get("form", "").strip()
        form_key = form.lower() if form else ""
        all_evos = []
        form_specific = evolution_map.get((name_lower, form_key), [])
        all_evos.extend(form_specific)
        if not form_specific:
            all_evos.extend(evolution_map.get((name_lower, ""), []))
        seen_targets = set()
        for evo in all_evos:
            evo_name_raw = evo["evolucion"]
            evo_src_form = evo.get("form", "").strip()
            target_form = ""
            evo_key = None
            # Determine target form and find matching pokemon_data entry
            if evo_src_form:
                target_form = evo.get("forma_evolucion", "").strip()
                if not target_form:
                    prefix = evo_src_form.split()[0]
                    target_form = f"{prefix} {evo_name_raw.capitalize()}"
                for k, v in pokemon_data.items():
                    if v["name"].lower() == evo_name_raw.lower() and v.get("form", "").strip().lower() == target_form.lower():
                        evo_key = k
                        break
            if not evo_key:
                evo_key = find_pokemon_by_base_name(evo_name_raw)
            if not evo_key or evo_key not in pokemon_data:
                continue
            target_key = (evo_name_raw.lower(), target_form.lower() if target_form else "")
            if target_key in seen_targets:
                continue
            seen_targets.add(target_key)
            evo_stats = pokemon_data[evo_key]
            method = evo["metodo"].strip()
            valor = evo["valor"].strip()
            can_evolve = False
            reason = ""

            if method == "Level":
                try:
                    req_level = int(valor)
                    if level_cap >= req_level:
                        can_evolve = True
                    else:
                        reason = f"Requires level {req_level} (cap: {level_cap})"
                except ValueError:
                    pass
            elif method == "Item":
                if valor.upper() in items_owned:
                    can_evolve = True
                else:
                    reason = f"Needs {valor}"
            elif method in ("TradeItem", "DayHoldItem"):
                if valor.upper() in items_owned:
                    can_evolve = True
                else:
                    reason = f"Needs {valor}"
            elif method in ("Happiness", "HappinessDay", "HappinessNight", "Trade", "TradeSpecies"):
                can_evolve = True
            elif method in ("LevelFemale", "LevelMale"):
                try:
                    req_level = int(valor)
                    if level_cap >= req_level:
                        can_evolve = True
                    else:
                        reason = f"Requires level {req_level} (cap: {level_cap})"
                except ValueError:
                    pass
            elif method in ("Ninjask", "Shedinja"):
                if level_cap >= 20:
                    can_evolve = True
                else:
                    reason = "Requires level 20"
            elif method in ("Silcoon", "Cascoon"):
                if level_cap >= 7:
                    can_evolve = True
                else:
                    reason = "Requires level 7"
            elif method in ("AttackGreater", "DefenseGreater", "AtkDefEqual"):
                can_evolve = True
            else:
                can_evolve = True

            item_needed = None
            evo_item = valor if method in ("Item", "TradeItem", "DayHoldItem") else None
            available.append({
                "from": c["name"],
                "from_form": c.get("form", ""),
                "to": evo_stats["name"],
                "to_form": target_form if target_form else evo_stats.get("form", ""),
                "method": method,
                "item": evo_item,
                "can_evolve": can_evolve,
                "reason": reason,
                "evo_stats": evo_stats,
            })
    return jsonify(available)

@app.route("/api/evolve", methods=["POST"])
def api_evolve():
    data = request.json
    from_name = data.get("from", "").strip()
    to_name = data.get("to", "").strip()
    from_form = data.get("form", "").strip()
    item = data.get("item")

    caught = get_caught()
    for i, c in enumerate(caught):
        name_match = c["name"].lower() == from_name.lower()
        form_match = True
        if from_form:
            form_match = c.get("form", "").strip().lower() == from_form.lower()
        if name_match and form_match:
            if item:
                item_key = item.upper()
                stock = has_item_stock(item_key)
                if stock < 1:
                    return jsonify({"error": f"Need {item} to evolve"}), 400
                consume_item(item_key)
            caught[i]["name"] = to_name
            # Find the target form based on evolution data
            old_form = c.get("form", "").strip()
            if old_form:
                evos = evolution_map.get((c["name"].lower(), old_form.lower()), [])
                target_form_csv = ""
                for evo in evos:
                    if evo["evolucion"].lower() == to_name.lower():
                        target_form_csv = evo.get("forma_evolucion", "").strip()
                        break
                if target_form_csv:
                    caught[i]["form"] = target_form_csv
                else:
                    prefix = old_form.split()[0]
                    candidate = f"{prefix} {to_name.capitalize()}"
                    found = any(
                        v["name"].lower() == to_name.lower() and v.get("form", "").strip().lower() == candidate.lower()
                        for v in pokemon_data.values()
                    )
                    caught[i]["form"] = candidate if found else ""
            save_json(CAUGHT_FILE, caught)
            return jsonify({"success": True, "new_name": to_name})
    return jsonify({"error": "Pokemon not found"}), 404

@app.route("/api/evolve-all", methods=["POST"])
def api_evolve_all():
    caught = get_caught()
    config = load_json(CONFIG_FILE, {"level_cap": 14})
    level_cap = config["level_cap"]
    evolved_count = 0
    evolved = []

    for i, c in enumerate(caught):
        name_lower = c["name"].lower()
        form = c.get("form", "").strip()
        form_key = form.lower() if form else ""
        all_evos = []
        all_evos.extend(evolution_map.get((name_lower, form_key), []))
        all_evos.extend(evolution_map.get((name_lower, ""), []))
        for evo in all_evos:
            method = evo["metodo"].strip()
            if method != "Level":
                continue
            try:
                req_level = int(evo["valor"].strip())
            except ValueError:
                continue
            if level_cap >= req_level:
                evo_form_col = evo.get("form", "").strip()
                if evo_form_col:
                    evo_key = None
                    for k, v in pokemon_data.items():
                        if v["name"].lower() == evo["evolucion"].lower() and v.get("form", "").strip().lower() == evo_form_col.lower():
                            evo_key = k
                            break
                else:
                    evo_key = find_pokemon_by_base_name(evo["evolucion"])
                if evo_key:
                    old_name = c["name"]
                    caught[i]["name"] = pokemon_data[evo_key]["name"]
                    if form:
                        target_form_csv = evo.get("forma_evolucion", "").strip()
                        if target_form_csv:
                            caught[i]["form"] = target_form_csv
                        else:
                            prefix = form.split()[0]
                            candidate = f"{prefix} {caught[i]['name'].capitalize()}"
                            found = any(
                                v["name"].lower() == caught[i]["name"].lower() and v.get("form", "").strip().lower() == candidate.lower()
                                for v in pokemon_data.values()
                            )
                            caught[i]["form"] = candidate if found else ""
                    evolved_count += 1
                    evolved.append(f"{old_name} -> {caught[i]['name']}")
                break

    save_json(CAUGHT_FILE, caught)
    return jsonify({"evolved": evolved_count, "details": evolved})

@app.route("/api/items/catalog")
def api_item_catalog():
    q = request.args.get("q", "").lower()
    results = []
    for code, nombre in item_catalog.items():
        display = f"{nombre}"
        if q in display.lower() or q in code.lower():
            results.append({"code": code, "name": nombre})
    return jsonify(sorted(results, key=lambda x: x["name"])[:20])

@app.route("/api/items", methods=["GET"])
def api_get_items():
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    save_json(ITEMS_FILE, items)
    return jsonify(items)

@app.route("/api/items", methods=["POST"])
def api_add_item():
    data = request.json
    item = data.get("item", "").strip().upper()
    quantity = int(data.get("quantity", 1))
    if not item:
        return jsonify({"error": "Item name required"}), 400
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    found = False
    for i in items:
        if i["name"] == item:
            i["stock"] += quantity
            found = True
            break
    if not found:
        items.append({"name": item, "stock": quantity})
    save_json(ITEMS_FILE, items)
    return jsonify(items)

@app.route("/api/items/<item>", methods=["DELETE"])
def api_remove_item(item):
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    items = [i for i in items if i["name"] != item.upper()]
    save_json(ITEMS_FILE, items)
    return jsonify(items)

@app.route("/api/items/<item>/decrement", methods=["POST"])
def api_decrement_item(item):
    n = request.json.get("quantity", 1) if request.json else 1
    for _ in range(n):
        consume_item(item.upper())
    items = load_json(ITEMS_FILE, [])
    items = migrate_items(items)
    return jsonify(items)

@app.route("/types/<filename>")
def serve_type_image(filename):
    return send_from_directory(os.path.join(DATA_DIR, "types"), filename)

@app.route("/api/compare")
def api_compare():
    name1 = request.args.get("name1", "").strip()
    name2 = request.args.get("name2", "").strip()
    if not name1 or not name2:
        return jsonify({"error": "Both names required"}), 400
    key1 = get_name_key(name1)
    key2 = get_name_key(name2)
    if not key1 or not key2:
        return jsonify({"error": "Pokemon not found"}), 404
    p1 = pokemon_data[key1]
    p2 = pokemon_data[key2]

    def calc_effectiveness(p):
        def_types = [p["type1"]]
        if p["type2"].strip():
            def_types.append(p["type2"].strip())
        results = {}
        for atk_type in all_types:
            mult = 1.0
            for dt in def_types:
                mult *= type_chart.get(atk_type, {}).get(dt, 1.0)
            if mult not in results:
                results[mult] = []
            results[mult].append(atk_type)
        return results

    return jsonify({
        "pokemon1": p1,
        "pokemon2": p2,
        "effectiveness1": calc_effectiveness(p1),
        "effectiveness2": calc_effectiveness(p2),
    })

_sprite_cache = {}

@app.route("/api/sprite/<name>")
def api_sprite(name):
    form = request.args.get("form", "")
    api_name = build_sprite_name(name, form)
    if api_name in _sprite_cache:
        return jsonify({"sprite": _sprite_cache[api_name]})
    sprite_url = f"https://pokeapi.co/api/v2/pokemon/{api_name}"
    try:
        resp = requests.get(sprite_url, timeout=5)
        if resp.status_code == 200:
            data_json = resp.json()
            sprite = data_json.get("sprites", {}).get("front_default", "")
            _sprite_cache[api_name] = sprite
            return jsonify({"sprite": sprite})
    except:
        pass
    return jsonify({"sprite": ""})

@app.route("/api/pokemon/forms")
def api_pokemon_forms():
    base_name = request.args.get("name", "").strip()
    forms = []
    for key, data in pokemon_data.items():
        if data["name"].lower() == base_name.lower():
            entry = dict(data)
            entry["sprite_name"] = build_sprite_name(data["name"], data.get("form", ""))
            entry["regional"] = is_regional_form(data.get("form", ""))
            forms.append(entry)
    return jsonify(forms)

if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
