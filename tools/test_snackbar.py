"""Offline test of the addon: real Lua 5.1 (lupa), a strict WoW mock and real items.

Usage: python tools/test_snackbar.py [addon folder]     (needs: pip install lupa)
"""
import csv
import pathlib
import sys

from lupa import lua51

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADDON = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "addon" / "Snack_Bar"

with open(ROOT / "tools" / "test_items.csv", encoding="utf-8", newline="") as f:
    ROWS = list(csv.DictReader(f))
SPELL = {int(r["id"]): int(r["spell"]) for r in ROWS if r["spell"]}
CLASS = {int(r["id"]): int(r["class"]) for r in ROWS}
ITEMS = {int(r["id"]): (r["name"], int(r["level"]), int(r["price"])) for r in ROWS}

MOCK = r"""
W = { combat = false, level = 10, bags = {}, unloaded = {}, instance = "none", map = 0, timers = {}, printed = {}, frames = {}, cooldown = {}, requested = {}, now = 0 }
local function protect(self, what)
	if W.combat and self.protected then error("PROTECTED in combat: " .. what, 3) end
end
local methods = {}
for _, name in ipairs({ "SetMovable", "SetClampedToScreen", "RegisterForDrag", "EnableMouse", "RegisterForClicks", "SetHighlightTexture",
	"SetPushedTexture", "SetAllPoints", "SetColorTexture", "SetTexCoord", "SetDrawEdge", "SetFrameStrata", "SetWidth", "SetFontObject",
	"SetMaxLetters", "SetJustifyH", "SetCursorPosition" }) do
	methods[name] = function() end
end
function methods:SetPoint(...) protect(self, "SetPoint"); self.point = { ... } end
function methods:ClearAllPoints() protect(self, "ClearAllPoints"); self.point = nil end
function methods:SetSize(w, h) protect(self, "SetSize"); self.w, self.h = w, h end
function methods:SetAttribute(k, v) protect(self, "SetAttribute"); self.attr[k] = v end
function methods:SetShown(v)
	protect(self, "SetShown")
	if type(v) ~= "boolean" then error("SetShown needs a boolean, got " .. tostring(v), 2) end
	local was = self.shown
	self.shown = v
	if was ~= v then
		local f = self.scripts[v and "OnShow" or "OnHide"]
		if f then f(self) end
	end
end
function methods:SetParent(p) protect(self, "SetParent"); self.parent = p; p.protected = true end
function methods:Show() self:SetShown(true) end
function methods:Hide() self:SetShown(false) end
function methods:IsShown() return self.shown end
function methods:SetScript(k, f) self.scripts[k] = f end
function methods:HookScript(k, f)
	local old = self.scripts[k]
	self.scripts[k] = function(...)
		if old then old(...) end
		f(...)
	end
end
function methods:SetDrawBling(v) if type(v) ~= "boolean" then error("bool") end self.bling = v end
function methods:SetAutoFocus(v) if type(v) ~= "boolean" then error("bool") end self.autoFocus = v end
function methods:GetText() return self.text_ end
function methods:ClearFocus()
	if self.focus then
		self.focus = false
		self.scripts.OnEditFocusLost(self)
	end
end
function methods:GetWidth() return 1600 end
function methods:GetHeight() return 900 end
function methods:SetClampRectInsets() protect(self, "SetClampRectInsets") end
function methods:IsMouseOver(top, bottom, left, right)
	if W.mouseOffBar == nil then return false end
	return W.mouseOffBar <= top and W.mouseOffBar <= -bottom and W.mouseOffBar <= -left and W.mouseOffBar <= right
end
function methods:RegisterEvent(e) self.events[e] = true end
function methods:UnregisterEvent(e) self.events[e] = nil end
function methods:CreateTexture() return NewObject("Texture", self) end
function methods:CreateFontString() return NewObject("FontString", self) end
function methods:GetFrameLevel() return 1 end
function methods:SetFrameLevel() end
function methods:SetTexture(t) self.texture = t end
function methods:SetDesaturated(v) if type(v) ~= "boolean" then error("bool") end self.desaturated = v end
function methods:SetAlpha(v) self.alpha = v end
function methods:SetText(t)
	if self.kind == "EditBox" and type(t) ~= "string" then error("SetText needs a string, got " .. type(t), 2) end
	self.text_ = tostring(t)
end
function methods:GetFont() return "font.ttf", 14, "OUTLINE" end
function methods:SetFont(_, size) self.fontSize = size end
function methods:SetCooldown(s, d) self.cd = { s, d } end
function methods:Clear() self.cd = nil end
function methods:StartMoving() protect(self, "StartMoving"); self.isMoving = true end
function methods:StopMovingOrSizing() protect(self, "StopMovingOrSizing"); self.isMoving = false end
function methods:GetLeft() return 700 end
function methods:GetTop() return 400 end
function methods:GetCenter() return 800, 450 end
function methods:SetChecked(v) self.checked = v end
function methods:GetChecked() return self.checked end
function methods:SetEnabled(v) if type(v) ~= "boolean" then error("bool") end self.enabledState = v end
function methods:Init(value, lo, hi, steps, formatters) self.value, self.lo, self.hi, self.step = value, lo, hi, (hi - lo) / steps end
function methods:SetValue(v) if v ~= self.value then self.value = v; if self.cb then self.cb(self.cbOwner, v) end end end
function methods:RegisterCallback(event, f, owner) self.cb, self.cbOwner = f, owner end
function NewObject(kind, parent)
	return setmetatable({ kind = kind, parent = parent, attr = {}, scripts = {}, events = {}, shown = true }, { __index = methods })
end
function CreateFrame(kind, name, parent, template)
	local f = NewObject(kind, parent)
	f.name, f.template = name, template
	if template == "SecureActionButtonTemplate" then
		f.protected = true
		parent.protected = true
	elseif template == "UICheckButtonTemplate" then f.Text = NewObject("FontString", f)
	elseif template == "UIRadioButtonTemplate" then f.text = NewObject("FontString", f)
	elseif template == "BasicFrameTemplateWithInset" then f.TitleText = NewObject("FontString", f)
	elseif template == "InputBoxTemplate" then f.autoFocus = true; f.scripts.OnEditFocusLost = function(self) self.highlightCleared = true end end
	if name then _G[name] = f end
	W.frames[#W.frames + 1] = f
	return f
end
UIParent = NewObject("Frame")
UISpecialFrames, SlashCmdList, tinsert = {}, {}, table.insert
GameTooltip = setmetatable({ SetOwner = function(s, o) s.owner = o end, IsOwned = function(s, o) return s.owner == o end,
	SetItemByID = function(s, id) s.item = id end, Show = function() end, Hide = function(s) s.owner = nil end }, {})
MinimalSliderWithSteppersMixin = { Event = { OnValueChanged = "OnValueChanged" } }
Enum = { ItemClass = { Consumable = 0 }, PowerType = { Mana = 0 } }
NUM_TOTAL_EQUIPPED_BAG_SLOTS = 5
function InCombatLockdown() return W.combat end
function UnitLevel() return W.level end
function UnitHealthMax() return 1000 end
function UnitPowerMax() return 1000 end
function issecretvalue() return false end
function GetInstanceInfo() return "x", W.instance, 0, "", 0, 0, false, W.map end
function print(text) W.printed[#W.printed + 1] = text end
function GetTime() return W.now end
-- Timers run at the next event, whatever their delay; the last delay is kept for the tests.
C_Timer = { After = function(delay, f) W.timers[#W.timers + 1] = f; W.delay = delay end }
C_Container = {
	GetContainerNumSlots = function(bag) return bag == 0 and #W.bags or 0 end,
	GetContainerItemID = function(_, slot) return W.bags[slot] and W.bags[slot][1] end,
}
C_Item = {
	GetItemInfoInstant = function(id) local c = PyClass(id); return id, "", "", "", 0, c, 0 end,
	GetItemInfo = function(id)
		if W.unloaded[id] then return nil end
		local name, level, price = PyItem(id)
		return name, "", 1, 1, level, "", "", 20, "", 0, price
	end,
	GetItemSpell = function(id) local s = PySpell(id); if s then return "spell", s end end,
	GetItemCount = function(id) local n = 0; for _, b in ipairs(W.bags) do if b[1] == id then n = n + b[2] end end return n end,
	GetItemCooldown = function(id) local c = W.cooldown[id]; if c then return c[1], c[2], true end return 0, 0, true end,
	GetItemIconByID = function(id) return "icon" .. id end,
	RequestLoadItemDataByID = function(id) W.requested[id] = true end,
}
function Fire(event, ...)
	for _, f in ipairs(W.frames) do
		if f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f, event, ...) end
	end
	local t = W.timers
	W.timers = {}
	for _, f in ipairs(t) do f() end
end
function Bags(...) W.bags = { ... }; Fire("BAG_UPDATE_DELAYED") end
"""


class Game:
    def __init__(self, saved=None, combat=False, **world):
        self.lua = lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        g = lua.globals()
        g.PyClass = lambda i: CLASS.get(i)
        g.PyItem = lambda i: ITEMS[i]
        g.PySpell = lambda i: SPELL.get(i)
        lua.execute(MOCK)
        self.w = g.W
        self.w.combat = combat
        for key, value in world.items():
            self.w[key] = value
        if saved:
            lua.execute("Snack_BarDB = " + saved)
        load = lua.eval("function(src, name, ns) local f = assert(loadstring(src, '@' .. name)); f('Snack_Bar', ns) end")
        self.ns = lua.table()
        toc = (ADDON / "Snack_Bar.toc").read_text(encoding="utf-8").splitlines()
        for file in (line.strip() for line in toc):
            if file and not file.startswith("#"):
                load((ADDON / file).read_text(encoding="utf-8"), file, self.ns)
        self.fire("ADDON_LOADED", "Snack_Bar")
        self.fire("PLAYER_LOGIN")
        self.fire("PLAYER_ENTERING_WORLD")

    def fire(self, event, *args):
        self.lua.globals().Fire(event, *args)

    def bags(self, *items):
        self.lua.globals().Bags(*[self.lua.table(i, n) for i, n in items])

    def slot(self, kind):
        return self.lua.globals()["Snack_Bar" + kind.capitalize()]

    def picked(self, kind):
        return self.slot(kind).itemID

    def tick(self):
        for f in list(self.w.frames.values()):
            if f.scripts.OnUpdate:
                f.scripts.OnUpdate(f, 0.2)

    def slash(self):
        self.lua.globals().SlashCmdList.SNACK_BAR("")

    def control(self, text):
        for f in self.w.frames.values():
            if f.label and f.label.text_ == text:
                yield f

    def click(self, text, index=0, checked=None):
        control = list(self.control(text))[index]
        if checked is not None:
            control.checked = checked
        control.scripts.OnClick(control)

    @property
    def fields(self):
        return [f for f in self.w.frames.values() if f.template == "InputBoxTemplate"]

    def type(self, field, text, key="OnEnterPressed"):
        field.focus, field.text_ = True, text
        field.scripts[key](field)

    def points(self, *kinds):
        """Offsets of the slots from the corner of their bar."""
        return [tuple(self.slot(k).point.values())[1:] for k in kinds]

    @property
    def settings(self):
        return self.lua.globals().Snack_BarDB

    @property
    def db(self):
        return self.settings.bars


# Items used below.
JERKY, BREAD, CONJURED_BREAD, CRAB_CLAW, QUAIL = 117, 4541, 1113, 2682, 8952
SPRING_WATER, MILK, PEACE_TEA = 159, 1179, 249865
MINOR_HP, LESSER_HP, HP, MINOR_MP, MAJOR_REJUV, SUP_DRAUGHT = 118, 858, 929, 2455, 18253, 17349
MANNA_BISCUIT, AB_RATION, HARVEST_BREAD, HEARTHSTONE, HEALTHSTONE = 19301, 20062, 19696, 6948, 5512
MAJOR_HP, SUPERIOR_HP, MAJOR_STONE, GREATER_STONE, WHIPPER_ROOT, MANA_AGATE = 13446, 3928, 9421, 5510, 11951, 5514

tests = []


def test(f):
    tests.append(f)
    return f


def equal(actual, expected, what=""):
    assert actual == expected, f"{what}: got {actual!r}, expected {expected!r}"


@test
def best_then_cheapest():
    g = Game()
    g.bags((JERKY, 20), (BREAD, 5), (SPRING_WATER, 5), (MILK, 5), (HEARTHSTONE, 1))
    equal(g.picked("food"), BREAD, "most restored")
    equal(g.picked("water"), MILK, "most restored")
    g.bags((JERKY, 20), (BREAD, 5), (CONJURED_BREAD, 5))
    equal(g.picked("food"), CONJURED_BREAD, "cheapest among equals")
    equal(g.slot("food").attr["*type1"], "item")
    equal(g.slot("food").attr["item"], f"item:{CONJURED_BREAD}")
    equal(g.slot("food").count.text_, "5")


@test
def required_level():
    g = Game()
    g.bags((JERKY, 1), (QUAIL, 5))
    equal(g.picked("food"), JERKY, "level 45 food at level 10")
    g.fire("PLAYER_LEVEL_UP", 45)
    equal(g.picked("food"), QUAIL, "after level up")


@test
def buff_food_is_last_resort():
    g = Game()
    g.bags((CRAB_CLAW, 3), (7737, 1), (PEACE_TEA, 2))
    equal(g.picked("food"), CRAB_CLAW, "only buff food")
    equal(g.picked("water"), PEACE_TEA, "only buff drink")
    g.bags((CRAB_CLAW, 3), (6299, 1), (PEACE_TEA, 2), (SPRING_WATER, 1))
    equal(g.picked("food"), 6299, "weaker plain food goes first")
    equal(g.picked("water"), SPRING_WATER)


@test
def combined_and_percent_food():
    g = Game(level=60)
    g.bags((MANNA_BISCUIT, 5), (QUAIL, 5), (MILK, 5))
    equal((g.picked("food"), g.picked("water")), (MANNA_BISCUIT, MANNA_BISCUIT), "counts for both slots")
    g.bags((HARVEST_BREAD, 5), (JERKY, 5), (4542, 5))
    equal(g.picked("food"), 4542, "50% of 1000 is less than 552")
    g.bags((HARVEST_BREAD, 5), (JERKY, 5), (BREAD, 5))
    equal(g.picked("food"), HARVEST_BREAD, "50% of 1000 is more than 244")


@test
def zone_limits():
    g = Game(level=60)
    g.bags((AB_RATION, 5), (JERKY, 1), (SUP_DRAUGHT, 5), (MINOR_HP, 1))
    equal((g.picked("food"), g.picked("health")), (JERKY, MINOR_HP), "outside")
    g.w.instance, g.w.map = "pvp", 529
    g.fire("PLAYER_ENTERING_WORLD")
    equal((g.picked("food"), g.picked("health")), (AB_RATION, SUP_DRAUGHT), "in Arathi Basin")
    g.w.map = 489
    g.fire("PLAYER_ENTERING_WORLD")
    equal((g.picked("food"), g.picked("health")), (JERKY, SUP_DRAUGHT), "in Warsong Gulch")


@test
def potions():
    g = Game(level=60)
    g.bags((MAJOR_REJUV, 3), (MINOR_HP, 1), (HP, 6), (HEALTHSTONE, 1))
    equal(g.picked("health"), HP, "combined potion is last, healthstones only with the option")
    equal(g.picked("mana"), MAJOR_REJUV, "last resort")
    equal(g.slot("health").attr["*type1"], "item", "6 of the best need no backup")
    g.bags((HP, 2), (LESSER_HP, 2), (MINOR_HP, 9), (MAJOR_REJUV, 1))
    equal(g.slot("health").attr["*type1"], "macro")
    equal(g.slot("health").attr["macrotext"], f"/use item:{HP}\n/use item:{LESSER_HP}\n/use item:{MINOR_HP}")


@test
def healthstones():
    g = Game(saved="{ bars = { potion = { enabled = true } } }", level=60)
    health = g.slot("health")
    g.bags((MAJOR_HP, 9), (MAJOR_STONE, 1), (WHIPPER_ROOT, 5), (MANA_AGATE, 1))
    equal((g.settings.healthstones, g.picked("health")), (False, MAJOR_HP), "off by default")
    g.slash()
    g.click("Healthstones as health potions", checked=True)
    equal(g.picked("health"), MAJOR_STONE, "1440 beats 1400")
    equal((health.attr["*type1"], health.attr["item"]), ("item", f"item:{MAJOR_STONE}"), "no potion behind it")
    g.bags((MAJOR_HP, 2), (GREATER_STONE, 1), (SUPERIOR_HP, 9))
    equal(g.picked("health"), MAJOR_HP, "960 loses to 1400")
    equal(health.attr["macrotext"], f"/use item:{MAJOR_HP}\n/use item:{SUPERIOR_HP}", "potion backups skip the stone")
    g.bags((GREATER_STONE, 1), (MAJOR_HP, 9), (MAJOR_STONE, 1))
    equal(health.attr["macrotext"], f"/use item:{MAJOR_STONE}\n/use item:{GREATER_STONE}", "stones back up stones")
    g.bags((WHIPPER_ROOT, 5), (MANA_AGATE, 1))
    equal(g.picked("health"), None, "same cooldown, but no healthstones")
    g.w.level = 40
    g.bags((MAJOR_STONE, 1), (GREATER_STONE, 1))
    equal(g.picked("health"), GREATER_STONE, "required level")
    stones = list(g.control("Healthstones as health potions"))[0]
    g.click("Health potions", checked=False)
    equal((stones.checked, stones.enabledState), (True, False), "needs the health slot")
    g.click("Health potions", checked=True)
    g.click("Show potions", checked=False)
    equal(stones.enabledState, False, "needs the potions")
    g.click("Show potions", checked=True)
    g.click("Healthstones as health potions", checked=False)
    g.bags((GREATER_STONE, 1), (SUPERIOR_HP, 1))
    equal(g.picked("health"), SUPERIOR_HP, "off again")


@test
def healthstone_in_combat():
    g = Game(saved="{ healthstones = true, bars = { potion = { enabled = true } } }", level=60)
    g.bags((MAJOR_STONE, 1), (MAJOR_HP, 9))
    g.fire("PLAYER_REGEN_DISABLED")
    g.w.combat = True
    g.bags((MAJOR_HP, 9))
    health = g.slot("health")
    equal((health.itemID, health.count.text_, health.icon.desaturated), (MAJOR_STONE, "0", True), "used up, no potion on that click")
    g.w.combat = False
    g.fire("PLAYER_REGEN_ENABLED")
    equal((g.picked("health"), health.attr["item"]), (MAJOR_HP, f"item:{MAJOR_HP}"), "potions after the fight")


@test
def healthstone_on_cooldown():
    g = Game(saved="{ healthstones = true, bars = { potion = { enabled = true } } }", level=60)
    g.w.now = 1000
    g.w.cooldown[MAJOR_STONE] = g.lua.table(950, 120)
    g.bags((MAJOR_STONE, 1), (MAJOR_HP, 9))
    equal((g.picked("health"), g.w.delay), (MAJOR_HP, 70), "a fresh stone waits for its cooldown")
    g.ns.Refresh()
    g.ns.Refresh()
    equal(len(list(g.w.timers.values())), 1, "one scan is enough")
    g.w.now = 1030
    g.fire("BAG_UPDATE_COOLDOWN")
    equal((g.picked("health"), g.w.delay), (MAJOR_HP, 40), "too early: waits again")
    g.w.now = 1070
    g.w.combat = True
    g.fire("BAG_UPDATE_COOLDOWN")
    equal(g.picked("health"), MAJOR_HP, "ready in combat: the button cannot change")
    g.w.combat = False
    g.fire("PLAYER_REGEN_ENABLED")
    equal(g.picked("health"), MAJOR_STONE, "after the fight")
    g.ns.Refresh()
    equal(len(list(g.w.timers.values())), 0, "nothing left to wait for")


@test
def combat_never_touches_secure_buttons():
    g = Game(saved="{ bars = { potion = { enabled = true } } }", level=20)
    g.bags((HP, 1), (LESSER_HP, 2), (BREAD, 5))
    g.fire("PLAYER_REGEN_DISABLED")
    g.w.combat = True
    g.bags((LESSER_HP, 2), (BREAD, 5), (QUAIL, 1))
    equal((g.picked("health"), g.slot("health").count.text_), (LESSER_HP, "2"), "shows the backup")
    g.bags((BREAD, 5))
    equal((g.slot("health").count.text_, g.slot("health").icon.desaturated), ("0", True), "ran out")
    assert g.slot("health").shown, "cannot hide in combat"
    g.w.combat = False
    g.fire("PLAYER_REGEN_ENABLED")
    assert not g.slot("health").shown, "hidden after combat"


@test
def login_in_combat():
    g = Game(combat=True)
    g.bags((BREAD, 5))
    assert g.slot("food") is None
    g.w.combat = False
    g.fire("PLAYER_REGEN_ENABLED")
    equal(g.picked("food"), BREAD)


@test
def empty_slots_are_hidden():
    g = Game()
    g.bags((BREAD, 5))
    assert g.slot("food").shown and not g.slot("water").shown
    g.slash()
    assert g.slot("water").shown, "visible while the options are open"
    equal(g.slot("water").icon.texture, "icon159")
    g.slash()
    assert not g.slot("water").shown


@test
def bars_and_slots():
    g = Game()
    g.bags((BREAD, 5), (MILK, 5), (HP, 1), (MINOR_HP, 1), (MINOR_MP, 1))
    main, potion = g.slot("food").parent, g.slot("health").parent
    assert main.shown and not potion.shown, "potions are off by default"
    equal((main.w, main.h), (84, 40))
    g.slash()
    g.click("Show potions", checked=True)
    assert potion.shown
    g.click("Vertical", 0)
    equal((main.w, main.h), (40, 84), "vertical")
    equal(tuple(g.slot("water").point.values()), ("TOPLEFT", 0, -44))
    equal((potion.w, potion.h), (84, 40), "bars are independent")
    g.click("Horizontal", 0)
    g.click("Food", checked=False)
    equal((main.w, main.h), (40, 40), "one slot left")
    assert not g.slot("food").shown and g.slot("water").shown
    equal(tuple(g.slot("water").point.values()), ("TOPLEFT", 0, 0), "moves up")
    g.click("Water", checked=False)
    assert not main.shown, "both off"
    g.click("Health potions", checked=False)
    assert potion.shown and g.slot("mana").shown and not g.slot("health").shown, "only mana potions"


@test
def resize():
    g = Game()
    g.bags((BREAD, 5))
    g.slash()
    sliders = [f for f in g.w.frames.values() if f.template == "MinimalSliderWithSteppersTemplate"]
    equal(len(sliders), 2)
    equal([s.step for s in sliders], [1, 1], "every typed number is a slider step")
    g.click("Show potions", checked=True)
    sliders[0].SetValue(sliders[0], 60)
    equal((g.slot("food").w, g.slot("health").w, g.settings.size), (60, 60, 60), "one size for both bars")
    equal(g.slot("food").count.fontSize, 21)
    equal((g.slot("food").parent.w, g.slot("health").parent.w), (124, 124))
    sliders[1].SetValue(sliders[1], 10)
    equal((g.slot("food").parent.w, g.slot("health").parent.w, g.settings.gap), (130, 130, 10), "one gap for both bars")
    equal(tuple(g.slot("water").point.values()), ("TOPLEFT", 70, 0))
    sliders[1].SetValue(sliders[1], 0)
    equal(tuple(g.slot("water").point.values()), ("TOPLEFT", 60, 0), "no gap")


@test
def attached_potions():
    g = Game()
    g.bags((BREAD, 5), (MILK, 5), (MINOR_HP, 1), (MINOR_MP, 1))
    main, potion = g.slot("food").parent, g.slot("health").parent
    attach = ("Separate bar", "Attach horizontally", "Attach vertically")
    g.slash()
    equal([c.enabledState for a in attach for c in g.control(a)], [False] * 3, "needs potions")
    g.click("Attach horizontally")
    equal((main.w, potion.shown), (84, False), "nothing to attach while potions are off")
    assert not g.slot("health").shown
    g.click("Show potions", checked=True)
    equal([c.enabledState for a in attach for c in g.control(a)], [True] * 3)
    equal([c.checked for a in attach for c in g.control(a)], [False, True, False])
    equal((main.w, main.h, potion.shown), (172, 40, False), "one bar of four")
    equal(g.points("food", "water", "health", "mana"), [(0, 0), (44, 0), (88, 0), (132, 0)])
    assert all(g.slot(k).shown and g.lua.eval("rawequal")(g.slot(k).parent, main) for k in ("food", "water", "health", "mana"))
    equal([c.enabledState for c in g.control("Vertical")], [True, False], "potions follow the main bar")
    g.click("Attach vertically")
    g.click("Vertical", 0)
    equal((main.w, main.h), (40, 172), "a column of four")
    equal(g.points("food", "water", "health", "mana"), [(0, 0), (0, -44), (0, -88), (0, -132)])
    equal([c.checked for c in g.control("Vertical")], [True, True])
    g.click("Food", checked=False)
    g.click("Water", checked=False)
    equal((main.w, main.h, main.shown), (40, 84, True), "only potions on the main bar")
    equal(g.points("health"), [(0, 0)])
    g.click("Separate bar")
    equal([c.checked for a in attach for c in g.control(a)], [True, False, False])
    assert potion.shown and not main.shown, "separate again"
    equal((potion.w, potion.h), (84, 40), "with its own direction")
    equal(tuple(potion.point.values())[3:], (-42, -220), "and its own place")
    g.click("Food", checked=True)
    g.click("Attach vertically")
    g.click("Show potions", checked=False)
    equal((main.w, main.h, main.shown), (40, 40, True), "potions gone")
    assert not g.slot("health").shown


@test
def square():
    g = Game(saved="{ bars = { potion = { enabled = true } } }")
    g.bags((BREAD, 5), (MILK, 5), (MINOR_HP, 1), (MINOR_MP, 1))
    main, all_kinds = g.slot("food").parent, ("food", "water", "health", "mana")
    g.slash()
    g.click("Attach vertically")
    equal((main.w, main.h), (84, 84), "potions below")
    equal(g.points(*all_kinds), [(0, 0), (44, 0), (0, -44), (44, -44)])
    equal((main.lip.point[1], main.lip.h), ("RIGHT", 28), "the lip stays at the start of the line")
    g.click("Vertical", 0)
    g.click("Attach horizontally")
    equal((main.w, main.h), (84, 84), "potions to the right")
    equal(g.points(*all_kinds), [(0, 0), (0, -44), (44, 0), (44, -44)])
    g.click("Water", checked=False)
    equal((main.w, main.h), (84, 84), "as long as the longest line")
    equal(g.points("food", "health", "mana"), [(0, 0), (44, 0), (44, -44)])
    g.click("Food", checked=False)
    equal((main.w, main.h), (40, 84), "no empty line")
    equal(g.points("health", "mana"), [(0, 0), (0, -44)])
    g.click("Food", checked=True)
    g.click("Water", checked=True)
    g.click("Mana potions", checked=False)
    equal((main.w, main.h), (84, 84))
    g.click("Health potions", checked=False)
    equal((main.w, main.h), (40, 84), "no line without potions")
    g.click("Mana potions", checked=True)
    g.type(g.fields[5], "0")
    equal((main.w, main.h), (80, 80), "no gap")
    equal(g.points("food", "water", "mana"), [(0, 0), (0, -40), (40, 0)])


@test
def show_on_hover():
    g = Game(saved="{ bars = { potion = { enabled = true } } }")
    g.bags((BREAD, 5), (MINOR_HP, 1))
    main, potion = g.slot("food").parent, g.slot("health").parent
    g.tick()
    equal((main.alpha, potion.alpha), (1, 1), "off by default")
    g.slash()
    g.click("Show only on mouse hover", checked=True)
    equal((main.alpha, potion.alpha), (1, 1), "visible while the options are open")
    g.tick()
    equal((main.alpha, potion.alpha), (1, 1), "and stays")
    g.slash()
    equal((main.alpha, potion.alpha), (0, 0), "hidden at once")
    g.w.mouseOffBar = 25
    g.tick()
    equal(main.alpha, 0, "not close enough")
    g.w.mouseOffBar = 15
    g.tick()
    equal((main.alpha, potion.alpha, main.lip.shown), (1, 1, True), "close")
    g.w.combat = True
    g.tick()
    equal((main.alpha, main.lip.shown), (1, False), "in combat too, without the lip")
    g.w.mouseOffBar = None
    g.tick()
    equal((main.alpha, main.shown, g.slot("food").shown), (0, True, True), "only the alpha changes in combat")
    g.w.combat = False
    main.lip.scripts.OnDragStart(main.lip)
    g.tick()
    equal((main.alpha, potion.alpha), (1, 0), "stays while dragging")
    main.lip.scripts.OnDragStop(main.lip)
    g.tick()
    equal(main.alpha, 0)
    equal(g.slot("food").cooldown.bling, False, "no flash on a hidden bar")
    g.slash()
    g.click("Show only on mouse hover", checked=False)
    g.slash()
    equal((main.alpha, potion.alpha), (1, 1), "off again")
    g = Game(saved="{ hover = true }")
    equal(g.lua.eval("function(f) return f.alpha end")(g.slot("food").parent), 0, "hidden from the start")
    g.slash()
    equal([c.checked for c in g.control("Show only on mouse hover")], [True])


@test
def typed_numbers():
    g = Game()
    g.bags((BREAD, 5))
    g.slash()
    equal(len(g.fields), 6)
    size, gap = g.fields[4:]
    sliders = [f for f in g.w.frames.values() if f.template == "MinimalSliderWithSteppersTemplate"]
    equal((size.text_, gap.text_, size.autoFocus), ("40", "4", False))
    g.type(size, "37")
    equal((g.settings.size, g.slot("food").w, sliders[0].value, size.text_), (37, 37, 37, "37"))
    assert size.highlightCleared, "keeps the script of the template"
    g.type(gap, " 12 ")
    equal((g.settings.gap, g.slot("food").parent.w, sliders[1].value), (12, 86, 12))
    for text, value in (("500", 80), ("1", 20), ("-30", 20), ("44.6", 45), ("50.", 50)):
        g.type(size, text)
        equal((g.settings.size, size.text_), (value, str(value)), text)
    for text in ("", "abc", "4x", "nan", "inf", "0x30", "1e1", "-", "--5", "4 4"):
        g.type(size, text)
        equal((g.settings.size, size.text_), (50, "50"), f"{text!r} is ignored")
    g.type(size, "60", "OnEscapePressed")
    equal((g.settings.size, size.text_), (50, "50"), "Escape restores")
    size.focus, size.text_ = True, "62"
    size.ClearFocus(size)
    equal((g.settings.size, g.slot("food").w), (62, 62), "a click elsewhere applies")
    sliders[0].SetValue(sliders[0], 30)
    equal((size.text_, g.slot("food").w), ("30", 30), "the field follows the slider")
    g.type(gap, "99")
    equal((g.settings.gap, gap.text_), (30, "30"))


@test
def typed_position():
    g = Game(saved="{ bars = { potion = { enabled = true } } }")
    g.bags((BREAD, 5), (MINOR_HP, 1))
    main, potion = g.slot("food").parent, g.slot("health").parent
    g.slash()
    equal([f.text_ for f in g.fields[:4]], ["-42", "-160", "-42", "-220"])
    g.type(g.fields[0], "261")
    g.type(g.fields[1], "-378")
    equal(tuple(main.point.values())[2:], ("CENTER", 261, -378))
    equal(tuple(potion.point.values())[2:], ("CENTER", -42, -220), "only that bar")
    g.type(g.fields[2], "261")
    g.type(g.fields[3], "-418")
    equal(tuple(potion.point.values())[2:], ("CENTER", 261, -418))
    g.type(g.fields[0], "-12.6")
    equal((g.db.main.x, g.fields[0].text_), (-13, "-13"), "whole pixels")
    for field, low, high in ((0, -800, 800), (1, -450, 450)):
        g.type(g.fields[field], "99999")
        equal(g.fields[field].text_, str(high), "not off the screen")
        g.type(g.fields[field], "-99999")
        equal(g.fields[field].text_, str(low), "not off the screen")
    main.lip.scripts.OnDragStart(main.lip)
    main.lip.scripts.OnDragStop(main.lip)
    equal([f.text_ for f in g.fields[:4]], ["-100", "-50", "261", "-418"], "follow a drag")
    equal([f.enabledState for f in g.fields[:4]], [True] * 4)
    g.click("Attach vertically")
    equal([f.enabledState for f in g.fields[:4]], [True, True, False, False], "attached potions have no place of their own")
    equal([f.alpha for f in g.fields[:4]], [1, 1, 0.4, 0.4])
    g.click("Separate bar")
    g.click("Show potions", checked=False)
    equal([f.enabledState for f in g.fields[:4]], [True, True, False, False])


@test
def closing_the_options_while_typing():
    g = Game()
    g.bags((BREAD, 5))
    g.slash()
    size = g.fields[4]
    for lockdown in (False, True):  # the client may report the lost focus before or after the lockdown starts
        size.focus, size.text_ = True, "6"
        g.fire("PLAYER_REGEN_DISABLED")
        g.w.combat = lockdown
        size.ClearFocus(size)
        equal((g.settings.size, size.text_, g.slot("food").w), (40, "40", 40), "combat drops it")
        g.w.combat = False
        g.fire("PLAYER_REGEN_ENABLED")
        g.slash()
        equal((g.settings.size, g.slot("food").w), (40, 40))
    size.focus, size.text_ = True, "50"
    g.slash()
    size.ClearFocus(size)
    equal((g.settings.size, g.slot("food").w), (50, 50), "closing the window applies it")


@test
def lip():
    g = Game()
    g.bags((BREAD, 5))
    bar, potion = g.slot("food").parent, g.slot("health").parent
    g.tick()
    assert not bar.lip.shown, "cursor elsewhere"
    g.w.mouseOffBar = 25
    g.tick()
    assert not bar.lip.shown, "not close enough"
    g.w.mouseOffBar = 15
    g.tick()
    assert bar.lip.shown, "close to the bar"
    equal((bar.lip.w, bar.lip.h, bar.lip.point[1]), (10, 28, "RIGHT"), "left of a horizontal bar")
    g.w.combat = True
    g.tick()
    assert not bar.lip.shown, "not in combat"
    g.w.combat = False
    g.bags()
    g.tick()
    assert not bar.lip.shown, "nothing visible to move"
    g.w.mouseOffBar = None
    g.slash()
    assert bar.lip.shown, "always there while the options are open"
    g.click("Vertical", 0)
    equal((bar.lip.w, bar.lip.h, bar.lip.point[1]), (28, 10, "BOTTOM"), "above a vertical bar")
    g.slash()
    assert not bar.lip.shown


@test
def lock():
    g = Game(saved="{ hover = true }")
    g.bags((BREAD, 5))
    bar = g.slot("food").parent
    g.slash()
    hint = g.lua.globals().Snack_BarOptions.hint
    assert bar.lip.shown and hint.shown
    g.click("Lock bars", checked=True)
    assert not bar.lip.shown and not hint.shown, "gone at once, also while the options are open"
    g.slash()
    g.w.mouseOffBar = 15
    g.tick()
    equal((bar.lip.shown, bar.alpha), (False, 1), "no lip near the bar, which still shows on hover")
    g.w.combat = True
    g.tick()
    equal((bar.lip.shown, bar.alpha), (False, 1))
    g.w.combat = False
    g.slash()
    equal([c.checked for c in g.control("Lock bars")], [True])
    g.type(g.fields[0], "100")
    equal(bar.point[4], 100, "a typed position still moves it")
    g.click("Lock bars", checked=False)
    assert bar.lip.shown and hint.shown
    g.slash()
    g.tick()
    assert bar.lip.shown, "back near the bar"
    g = Game(saved="{ locked = true }")
    g.bags((BREAD, 5))
    g.w.mouseOffBar = 0
    g.tick()
    assert not g.slot("food").parent.lip.shown, "locked from the start"
    g.slash()
    equal([c.checked for c in g.control("Lock bars")], [True])


@test
def moving():
    g = Game()
    g.bags((BREAD, 5))
    bar = g.slot("food").parent
    bar.lip.scripts.OnDragStart(bar.lip)
    assert bar.isMoving
    g.tick()
    assert bar.lip.shown, "stays while dragging"
    bar.lip.scripts.OnDragStop(bar.lip)
    g.tick()
    assert not bar.lip.shown
    equal((g.db.main.x, g.db.main.y), (-100, -50))
    equal(tuple(bar.point.values())[2:], ("CENTER", -100, -50))


@test
def combat_stops_a_drag():
    g = Game()
    g.bags((BREAD, 5))
    bar = g.slot("food").parent
    bar.lip.scripts.OnDragStart(bar.lip)
    g.fire("PLAYER_REGEN_DISABLED")
    g.w.combat = True
    g.tick()
    assert not bar.isMoving and not bar.lip.shown
    equal((g.db.main.x, g.db.main.y), (-100, -50), "saved where it was dropped")
    bar.lip.scripts.OnDragStart(bar.lip)
    assert not bar.isMoving, "cannot start one in combat"


@test
def options_close_when_combat_starts():
    g = Game()
    g.bags((BREAD, 5))
    g.slash()
    g.fire("PLAYER_REGEN_DISABLED")
    g.w.combat = True
    assert not g.lua.globals().Snack_BarOptions.shown and not g.slot("food").parent.lip.shown
    assert not g.slot("water").shown
    g.slash()
    assert not g.lua.globals().Snack_BarOptions.shown
    equal(len(list(g.w.printed.values())), 1)


@test
def late_item_data():
    g = Game()
    g.w.unloaded[BREAD] = True
    g.bags((BREAD, 5))
    assert g.w.requested[BREAD] and not g.picked("food")
    g.w.unloaded[BREAD] = None
    g.fire("ITEM_DATA_LOAD_RESULT", BREAD, True)
    equal(g.picked("food"), BREAD)


@test
def cooldown():
    g = Game(level=20)
    g.bags((HP, 5))
    g.w.cooldown[HP] = g.lua.table(100, 120)
    g.fire("BAG_UPDATE_COOLDOWN")
    equal(tuple(g.slot("health").cooldown.cd.values()), (100, 120))
    g.w.cooldown[HP] = None
    g.fire("BAG_UPDATE_COOLDOWN")
    equal(g.slot("health").cooldown.cd, None)


@test
def saved_settings_survive():
    g = Game(saved="{ size = 64, bars = { main = { slots = { water = false } }, potion = { enabled = true } } }")
    g.bags((BREAD, 5), (MILK, 5))
    equal((g.settings.size, g.settings.gap, g.settings.attach, g.settings.hover, g.settings.locked), (64, 4, False, False, False))
    equal((g.db.main.slots.water, g.db.main.slots.food, g.db.potion.enabled, g.slot("food").w), (False, True, True, 64))
    assert g.slot("food").shown and not g.slot("water").shown


failed = 0
for t in tests:
    try:
        t()
        print("ok  ", t.__name__)
    except Exception as e:
        failed += 1
        print("FAIL", t.__name__, "-", str(e).splitlines()[0])
print(f"{len(tests) - failed}/{len(tests)} passed")
sys.exit(bool(failed))
