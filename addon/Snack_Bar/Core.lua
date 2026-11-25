local ADDON, ns = ...

ns.BARS = {
	{ key = "main", label = "Food & Water", kinds = { "food", "water" } },
	{ key = "potion", label = "Potions", kinds = { "health", "mana" } },
}

ns.KIND_LABELS = { food = "Food", water = "Water", health = "Health potions", mana = "Mana potions" }

local DEFAULTS = {
	size = 40,
	gap = 4,
	attach = false, -- potions on the food and water bar: "horizontal" (beside) or "vertical" (below)
	hover = false, -- bars are only visible while the mouse is near
	locked = false, -- no lips, so bars cannot be dragged
	bars = {
		main = { enabled = true, vertical = false, x = -42, y = -160, slots = { food = true, water = true } },
		potion = { enabled = false, vertical = false, x = -42, y = -220, slots = { health = true, mana = true } },
	},
}

local function ApplyDefaults(target, defaults)
	for key, value in pairs(defaults) do
		if type(value) == "table" then
			if type(target[key]) ~= "table" then
				target[key] = {}
			end
			ApplyDefaults(target[key], value)
		elseif target[key] == nil then
			target[key] = value
		end
	end
end

-- Finding snacks ------------------------------------------------------------

local snackCache = {} -- itemID -> { data, minLevel, price }, or false when the item is no snack
local pendingItems = {}

local function GetSnack(itemID)
	local snack = snackCache[itemID]
	if snack ~= nil then
		return snack
	end
	local _, _, _, _, _, classID = C_Item.GetItemInfoInstant(itemID)
	if not classID then
		return nil
	end
	if classID ~= Enum.ItemClass.Consumable then
		snackCache[itemID] = false
		return false
	end
	local name, _, _, _, minLevel, _, _, _, _, _, price = C_Item.GetItemInfo(itemID)
	if not name then
		pendingItems[itemID] = true
		C_Item.RequestLoadItemDataByID(itemID)
		return nil
	end
	local _, spellID = C_Item.GetItemSpell(itemID)
	if not spellID then
		return nil
	end
	local data = ns.SPELLS[spellID]
	snack = data and { data = data, minLevel = minLevel or 0, price = price or 0 } or false
	snackCache[itemID] = snack
	return snack
end

-- Maximum health and mana turn percentages into amounts. They can be secret values
-- in restricted situations; the last readable value is good enough for ranking.
local maximum = { food = 1, water = 1, health = 1, mana = 1 }

local function UpdateMaximums()
	local health = UnitHealthMax("player")
	if not issecretvalue(health) then
		maximum.food, maximum.health = health, health
	end
	local mana = UnitPowerMax("player", Enum.PowerType.Mana)
	if not issecretvalue(mana) then
		maximum.water, maximum.mana = mana, mana
	end
end

local function GetAmount(data, kind)
	return (data[kind] or 0) + (data[kind .. "Pct"] or 0) / 100 * maximum[kind]
end

-- Plain items before buff food and the like, then the most restored, then the cheapest.
-- The last two rules only keep the order stable: smallest stack first, then item id.
local function IsBetter(a, b)
	if a.last ~= b.last then
		return b.last
	end
	if a.amount ~= b.amount then
		return a.amount > b.amount
	end
	if a.price ~= b.price then
		return a.price < b.price
	end
	if a.count ~= b.count then
		return a.count < b.count
	end
	return a.itemID < b.itemID
end

local levelReached = 0

-- Returns, per kind, the usable items in the bags, best first.
function ns.Scan()
	UpdateMaximums()
	local level = math.max(UnitLevel("player"), levelReached)
	local _, instanceType, _, _, _, _, _, mapID = GetInstanceInfo()
	local lists = { food = {}, water = {}, health = {}, mana = {} }
	local seen = {}
	for bag = 0, NUM_TOTAL_EQUIPPED_BAG_SLOTS do
		for bagSlot = 1, C_Container.GetContainerNumSlots(bag) do
			local itemID = C_Container.GetContainerItemID(bag, bagSlot)
			if itemID and not seen[itemID] then
				seen[itemID] = true
				local snack = GetSnack(itemID)
				local data = snack and snack.data
				if data and snack.minLevel <= level
					and (not data.pvp or instanceType == "pvp")
					and (not data.map or data.map == mapID) then
					for kind, list in pairs(lists) do
						local amount = GetAmount(data, kind)
						if amount > 0 then
							list[#list + 1] = {
								itemID = itemID,
								amount = amount,
								price = snack.price,
								count = C_Item.GetItemCount(itemID),
								last = data.last or false,
							}
						end
					end
				end
			end
		end
	end
	for _, list in pairs(lists) do
		table.sort(list, IsBetter)
	end
	return lists
end

-- Refreshing ----------------------------------------------------------------

local started = false
local refreshQueued = false
local refreshAfterCombat = false

function ns.Refresh()
	if not started then
		return
	end
	if InCombatLockdown() then
		-- Secure buttons cannot change in combat: keep their items, update icons and counts.
		refreshAfterCombat = true
	else
		refreshAfterCombat = false
		ns.ApplyLists(ns.Scan())
	end
	ns.UpdateDisplay()
end

local function QueueRefresh()
	if refreshQueued then
		return
	end
	refreshQueued = true
	C_Timer.After(0, function()
		refreshQueued = false
		ns.Refresh()
	end)
end

local function Start()
	started = true
	ns.CreateBars()
	ns.ApplySettings()
end

-- Events --------------------------------------------------------------------

local events = CreateFrame("Frame")
local handlers = {}

function handlers.ADDON_LOADED(name)
	if name == ADDON then
		events:UnregisterEvent("ADDON_LOADED")
		Snack_BarDB = Snack_BarDB or {}
		ApplyDefaults(Snack_BarDB, DEFAULTS)
		ns.db = Snack_BarDB
	end
end

function handlers.PLAYER_LOGIN()
	if not InCombatLockdown() then
		Start()
	end
end

function handlers.PLAYER_REGEN_ENABLED()
	if not started then
		Start()
	elseif refreshAfterCombat then
		ns.Refresh()
	end
end

function handlers.PLAYER_REGEN_DISABLED()
	ns.StopMovingBars()
	ns.CloseOptions()
end

function handlers.PLAYER_LEVEL_UP(level)
	levelReached = level
	QueueRefresh()
end

function handlers.ITEM_DATA_LOAD_RESULT(itemID, success)
	if pendingItems[itemID] then
		pendingItems[itemID] = nil
		if success then
			QueueRefresh()
		end
	end
end

function handlers.BAG_UPDATE_COOLDOWN()
	if started then
		ns.UpdateCooldowns()
	end
end

handlers.BAG_UPDATE_DELAYED = QueueRefresh
handlers.PLAYER_ENTERING_WORLD = QueueRefresh

events:SetScript("OnEvent", function(_, event, ...)
	handlers[event](...)
end)
for event in pairs(handlers) do
	events:RegisterEvent(event)
end
