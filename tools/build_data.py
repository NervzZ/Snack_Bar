"""Generate addon/Snack_Bar/Data.lua from the game client's own tables (wago.tools DB2 export).

Also writes tools/test_items.csv, the items the offline tests put in the bags.

Usage: python tools/build_data.py 1.60.1.71037

The table is keyed by SPELL id (what C_Item.GetItemSpell returns), because new foods mostly
reuse existing spells and spell ids do not depend on the client language.
"""
import collections
import csv
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "addon" / "Snack_Bar" / "Data.lua"
TEST_ITEMS = ROOT / "tools" / "test_items.csv"
OTHER_TEST_ITEMS = [5512, 6948, 7737]  # no food or potions: Minor Healthstone, Hearthstone, Sethir's Journal
TABLES = ["Item", "ItemSparse", "ItemEffect", "ItemXItemEffect", "SpellName", "SpellEffect", "Spell",
          "SpellMisc", "SpellDuration", "SpellCastingRequirements", "AreaGroupMember", "AreaTable"]

CONSUMABLE = "0"
SUB_POTION, SUB_FOOD = "1", "5"
CAT_POTION, CAT_FOOD, CAT_DRINK = "4", "11", "59"
# Effects and auras.
E_HEAL, E_AURA, E_ENERGIZE, E_TRIGGER, E_HEAL_PCT, E_ENERGIZE_PCT = 10, 6, 30, 64, 136, 137
A_HEALTH, A_MANA, A_HEALTH_PCT, A_MANA_PCT, A_PERIODIC_DUMMY = 84, 85, 20, 21, 226
BUFF_TEXT = re.compile(r"well fed|increases? your|become refreshed", re.I)
PVP_TEXT = re.compile(r"only be used in PvP Battlegrounds", re.I)


def load(build):
    cache = ROOT / "tools" / "cache" / build
    cache.mkdir(parents=True, exist_ok=True)
    data = {}
    for table in TABLES:
        path = cache / f"{table}.csv"
        if not path.exists():
            request = urllib.request.Request(f"https://wago.tools/db2/{table}/csv?build={build}",
                                             headers={"User-Agent": "Mozilla/5.0"})
            path.write_bytes(urllib.request.urlopen(request).read())
        with open(path, encoding="utf-8", newline="") as f:
            data[table] = list(csv.DictReader(f))
        assert data[table], f"{table} is empty"
    return data


class Spells:
    def __init__(self, data):
        self.effects = collections.defaultdict(list)
        self.scaling = set()
        for row in data["SpellEffect"]:
            if row["DifficultyID"] == "0":
                self.effects[int(row["SpellID"])].append(row)
        durations = {row["ID"]: int(row["Duration"]) / 1000 for row in data["SpellDuration"]}
        self.duration = {}
        for row in data["SpellMisc"]:
            if row["DifficultyID"] == "0":
                self.duration[int(row["SpellID"])] = durations.get(row["DurationIndex"], 0)
        self.text = {int(row["ID"]): row["Description_lang"] for row in data["Spell"]}
        self.name = {int(row["ID"]): row["Name_lang"] for row in data["SpellName"]}
        continent = {row["ID"]: int(row["ContinentID"]) for row in data["AreaTable"]}
        group = collections.defaultdict(set)
        for row in data["AreaGroupMember"]:
            if row["AreaID"] in continent:
                group[row["AreaGroupID"]].add(continent[row["AreaID"]])
        self.maps = {int(row["SpellID"]): group[row["RequiredAreasID"]]
                     for row in data["SpellCastingRequirements"] if row["RequiredAreasID"] != "0"}

    def analyse(self, spell, depth=0):
        """Return (over_time, instant, side_effect): amounts by 'health'/'mana'/'healthPct'/'manaPct'."""
        over_time, instant = collections.Counter(), collections.Counter()
        side_effect = False
        seconds = self.duration.get(spell, 0)
        for row in self.effects[spell]:
            effect, aura = int(row["Effect"]), int(row["EffectAura"])
            points, misc = float(row["EffectBasePointsF"]), int(row["EffectMiscValue_0"])
            if float(row["EffectRealPointsPerLevel"]):
                self.scaling.add(spell)
            if effect == E_AURA and aura in (A_HEALTH, A_MANA):
                over_time["health" if aura == A_HEALTH else "mana"] += points * seconds / 5
            elif effect == E_AURA and aura in (A_HEALTH_PCT, A_MANA_PCT):
                period = int(row["EffectAuraPeriod"]) / 1000 or 1
                over_time["healthPct" if aura == A_HEALTH_PCT else "manaPct"] += points * seconds / period
            elif effect == E_HEAL:
                instant["health"] += points
            elif effect == E_HEAL_PCT:
                instant["healthPct"] += points
            elif effect == E_ENERGIZE and misc == 0:
                instant["mana"] += points
            elif effect == E_ENERGIZE_PCT and misc == 0:
                instant["manaPct"] += points
            elif effect == E_TRIGGER and depth == 0 and row["EffectTriggerSpell"] != "0":
                sub_time, sub_instant, sub_side = self.analyse(int(row["EffectTriggerSpell"]), 1)
                over_time.update(sub_time)
                instant.update(sub_instant)
                side_effect |= sub_side or not (sub_time or sub_instant)
            elif effect == E_AURA and aura == A_PERIODIC_DUMMY:
                pass
            else:
                side_effect = True
        return over_time, instant, side_effect


def build(data):
    spells = Spells(data)
    items = {int(row["ID"]): row for row in data["Item"]}
    names = {int(row["ID"]): row["Display_lang"] for row in data["ItemSparse"]}
    effects = {int(row["ID"]): row for row in data["ItemEffect"]}
    entries, users, snacks = {}, collections.defaultdict(list), set()
    for link in data["ItemXItemEffect"]:
        item_id, use = int(link["ItemID"]), effects.get(int(link["ItemEffectID"]))
        item = items.get(item_id)
        if not (item and use) or item["ClassID"] != CONSUMABLE or use["TriggerType"] != "0" or item_id not in names:
            continue
        # A player condition here means "needs some other item equipped": not plainly usable.
        if use["PlayerConditionID"] != "0":
            continue
        spell, category, subclass = int(use["SpellID"]), use["SpellCategoryID"], item["SubclassID"]
        over_time, instant, side_effect = spells.analyse(spell)
        text = spells.text.get(spell, "")
        entry = {}
        if over_time and category != CAT_POTION and (subclass == SUB_FOOD or category in (CAT_FOOD, CAT_DRINK)):
            for source, kind in (("health", "food"), ("mana", "water"), ("healthPct", "foodPct"), ("manaPct", "waterPct")):
                if over_time[source] > 0:
                    entry[kind] = over_time[source]
            entry["last"] = bool(side_effect or BUFF_TEXT.search(text))
        elif instant and not over_time and category == CAT_POTION and subclass != SUB_FOOD:
            for source in ("health", "mana", "healthPct", "manaPct"):
                if instant[source] > 0:
                    entry[source] = instant[source]
            both = any(k.startswith("health") for k in entry) and any(k.startswith("mana") for k in entry)
            entry["last"] = bool(side_effect or both)
        if not any(key != "last" for key in entry):
            continue
        assert spell not in spells.scaling, f"spell {spell} scales with level"
        entry["pvp"] = bool(PVP_TEXT.search(text))
        maps = spells.maps.get(spell)
        if maps:
            # Limited to zones of a continent (0, 1): a map check cannot tell, so leave the spell out.
            if len(maps) > 1 or maps & {0, 1}:
                print(f"skipped {spell} ({names[item_id]}): limited to zones on maps {sorted(maps)}")
                continue
            entry["map"] = next(iter(maps))
        assert entries.setdefault(spell, entry) == entry, f"spell {spell} differs between items"
        users[spell].append(names[item_id])
        snacks.add(item_id)
    return spells, entries, users, snacks


def write_test_items(data, ids):
    use = {row["ID"]: row["SpellID"] for row in data["ItemEffect"] if row["TriggerType"] == "0"}
    spell = {int(row["ItemID"]): use[row["ItemEffectID"]] for row in data["ItemXItemEffect"] if row["ItemEffectID"] in use}
    item_class = {int(row["ID"]): row["ClassID"] for row in data["Item"]}
    items = {int(row["ID"]): row for row in data["ItemSparse"]}
    with open(TEST_ITEMS, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["id", "name", "class", "level", "price", "spell"])
        for i in sorted(ids):
            writer.writerow([i, items[i]["Display_lang"], item_class[i], items[i]["RequiredLevel"], items[i]["SellPrice"], spell.get(i, "")])


def lua(entry):
    parts = []
    for key in ("food", "water", "foodPct", "waterPct", "health", "mana", "healthPct", "manaPct", "map"):
        if entry.get(key):
            parts.append(f"{key} = {round(entry[key])}")
    parts += [f"{key} = true" for key in ("last", "pvp") if entry.get(key)]
    return "{ " + ", ".join(parts) + " }"


def main(build_id):
    data = load(build_id)
    spells, entries, users, snacks = build(data)
    lines = [f"-- Generated by tools/build_data.py from client data {build_id}. Do not edit by hand.",
             "-- [spellID] = total amount restored per kind (Pct = percent of the maximum).",
             "-- last = buff, side effect or combined potion: used only when nothing plain is available.",
             "-- map / pvp = usable only on that map / in battlegrounds.",
             "local _, ns = ...", "", "ns.SPELLS = {"]
    for spell in sorted(entries):
        extra = len(users[spell]) - 1
        label = users[spell][0] + (f" +{extra}" if extra else "")
        lines.append(f"\t[{spell}] = {lua(entries[spell])}, -- {spells.name[spell]}: {label}")
    lines += ["}", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    write_test_items(data, snacks.union(OTHER_TEST_ITEMS))
    print(f"{len(entries)} spells, {sum(map(len, users.values()))} items -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
