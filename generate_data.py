import csv, json

pokemon_data = {}
with open("Pokemon.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row["Name"]
        form = row.get("Form", "").strip()
        key = f"{name}|{form}" if form and form != " " else name
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

evolution_map = {}
with open("pokemon_evoluciones.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pre = row["pokemon"].strip().lower()
        form = row.get("form", "").strip().lower()
        key = f"{pre}|{form}"
        if key not in evolution_map:
            evolution_map[key] = []
        evolution_map[key].append({
            "pokemon": row["pokemon"].strip(),
            "evolucion": row["evolucion"].strip(),
            "metodo": row["metodo"].strip(),
            "valor": row["valor"].strip(),
            "form": row.get("form", "").strip(),
            "forma_evolucion": row.get("forma_evolucion", "").strip(),
        })

item_catalog = {}
with open("items.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        nombre = row["nombre"].strip()
        valor = row["valor"].strip()
        item_catalog[valor.upper()] = nombre

type_chart = {}
all_types = []
with open("Pokemon Type Chart.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    headers = next(reader)
    all_types = [h.strip() for h in headers[1:] if h.strip()]
    for row in reader:
        attacking = row[0].strip()
        type_chart[attacking] = {}
        for i, val in enumerate(row[1:]):
            if i < len(all_types):
                type_chart[attacking][all_types[i]] = float(val)

lines = []
lines.append("// Auto-generated data file. Run python generate_data.py to regenerate.")
lines.append("const POKEMON_DATA = " + json.dumps(pokemon_data, ensure_ascii=False, indent=0) + ";")
lines.append("const EVOLUTION_MAP = " + json.dumps(evolution_map, ensure_ascii=False, indent=0) + ";")
lines.append("const ITEM_CATALOG = " + json.dumps(item_catalog, ensure_ascii=False, indent=0) + ";")
lines.append("const TYPE_CHART = " + json.dumps(type_chart, ensure_ascii=False) + ";")
lines.append("const ALL_TYPES = " + json.dumps(all_types, ensure_ascii=False) + ";")

with open("data.js", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Generated data.js")
print(f"  Pokemon: {len(pokemon_data)} entries")
print(f"  Evolutions: {len(evolution_map)} keys")
print(f"  Items catalog: {len(item_catalog)} entries")
print(f"  Types: {len(all_types)}")
