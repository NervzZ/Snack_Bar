local _, ns = ...

local LIP_THICKNESS, LIP_GAP, LIP_REACH = 10, 2, 20
-- A potion button holds enough backups to last a fight, since it cannot change in combat.
local BACKUP_COUNT, BACKUP_LINES = 5, 6
local BUTTON_NAMES = { food = "Snack_BarFood", water = "Snack_BarWater", health = "Snack_BarHealth", mana = "Snack_BarMana" }
local PLACEHOLDER_ITEMS = { food = 4540, water = 159, health = 118, mana = 2455 }

local bars, slots = {}, {}

-- Slots ---------------------------------------------------------------------

local function ShowTooltip(slot)
	if slot.itemID then
		GameTooltip:SetOwner(slot, "ANCHOR_RIGHT")
		GameTooltip:SetItemByID(slot.itemID)
		GameTooltip:Show()
	end
end

local function HideTooltip(slot)
	if GameTooltip:IsOwned(slot) then
		GameTooltip:Hide()
	end
end

local function CreateSlot(bar, kind)
	local slot = CreateFrame("Button", BUTTON_NAMES[kind], bar, "SecureActionButtonTemplate")
	slot.kind = kind
	slot.home = bar
	slot.isPotion = kind == "health" or kind == "mana"
	slot.list = {}
	slot.active = 0
	slot:RegisterForClicks("AnyUp", "AnyDown")
	slot:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
	slot:SetPushedTexture("Interface\\Buttons\\UI-Quickslot-Depress")
	slot:SetScript("OnEnter", ShowTooltip)
	slot:SetScript("OnLeave", HideTooltip)

	local background = slot:CreateTexture(nil, "BACKGROUND")
	background:SetAllPoints()
	background:SetColorTexture(0, 0, 0, 0.7)

	slot.icon = slot:CreateTexture(nil, "ARTWORK")
	slot.icon:SetPoint("TOPLEFT", 1, -1)
	slot.icon:SetPoint("BOTTOMRIGHT", -1, 1)
	slot.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)

	slot.cooldown = CreateFrame("Cooldown", nil, slot, "CooldownFrameTemplate")
	slot.cooldown:SetAllPoints(slot.icon)
	slot.cooldown:SetDrawEdge(false)
	slot.cooldown:SetDrawBling(false) -- like the action bars; the flash would show on a hidden bar

	-- The count sits on its own frame so the cooldown swipe does not cover it.
	local overlay = CreateFrame("Frame", nil, slot)
	overlay:SetAllPoints()
	overlay:SetFrameLevel(slot.cooldown:GetFrameLevel() + 1)
	slot.count = overlay:CreateFontString(nil, "OVERLAY", "NumberFontNormal")
	slot.count:SetPoint("BOTTOMRIGHT", -2, 2)
	return slot
end

local function SetAction(slot)
	local best = slot.list[1]
	if not best then
		slot.active = 0
		slot:SetAttribute("*type1", nil)
	elseif slot.isPotion and slot.list[2] and best.count < BACKUP_COUNT then
		local lines, total = {}, 0
		for index, entry in ipairs(slot.list) do
			lines[index] = "/use item:" .. entry.itemID
			total = total + entry.count
			if total >= BACKUP_COUNT or index == BACKUP_LINES then
				break
			end
		end
		slot.active = #lines
		slot:SetAttribute("macrotext", table.concat(lines, "\n"))
		slot:SetAttribute("*type1", "macro")
	else
		slot.active = 1
		slot:SetAttribute("item", "item:" .. best.itemID)
		slot:SetAttribute("*type1", "item")
	end
end

-- Out of combat only.
function ns.ApplyLists(lists)
	for _, slot in ipairs(slots) do
		slot.list = lists[slot.kind]
		SetAction(slot)
		slot:SetShown(slot.enabled and (slot.list[1] ~= nil or ns.optionsOpen or false))
	end
end

local function UpdateCooldown(slot)
	if slot.itemID then
		local start, duration, enabled = C_Item.GetItemCooldown(slot.itemID)
		if start and start > 0 and duration > 0 and enabled then
			slot.cooldown:SetCooldown(start, duration)
			return
		end
	end
	slot.cooldown:Clear()
end

function ns.UpdateCooldowns()
	for _, slot in ipairs(slots) do
		UpdateCooldown(slot)
	end
end

-- Safe in combat: shows the item the button would use right now.
function ns.UpdateDisplay()
	for _, slot in ipairs(slots) do
		local entry, count = slot.list[1], 0
		for index = 1, slot.active do
			local available = C_Item.GetItemCount(slot.list[index].itemID)
			if available > 0 then
				entry, count = slot.list[index], available
				break
			end
		end
		slot.itemID = entry and entry.itemID
		slot.icon:SetTexture(C_Item.GetItemIconByID(slot.itemID or PLACEHOLDER_ITEMS[slot.kind]))
		slot.icon:SetDesaturated(count == 0)
		slot.icon:SetAlpha(entry and 1 or 0.4)
		slot.count:SetText(entry and count or "")
		UpdateCooldown(slot)
		if GameTooltip:IsOwned(slot) then
			ShowTooltip(slot)
		end
	end
end

-- Bars ----------------------------------------------------------------------

local function Place(bar)
	local config = ns.db.bars[bar.key]
	bar:ClearAllPoints()
	bar:SetPoint("TOPLEFT", UIParent, "CENTER", config.x, config.y)
end

local function StopMoving(bar)
	if bar.moving then
		bar.moving = false
		bar:StopMovingOrSizing()
		local config = ns.db.bars[bar.key]
		local centerX, centerY = UIParent:GetCenter()
		config.x = math.floor(bar:GetLeft() - centerX + 0.5)
		config.y = math.floor(bar:GetTop() - centerY + 0.5)
		Place(bar)
		ns.UpdateOptions()
	end
end

-- The lip is a small tab at the start of a bar: it shows when the cursor is near and drags the bar.
local function HasVisibleSlot(bar)
	for _, slot in ipairs(bar.slots) do
		if slot:IsShown() then
			return true
		end
	end
	return false
end

-- A bar hides by its alpha, because its secure buttons cannot be hidden or shown in combat.
local function UpdateHover(bar)
	local near = HasVisibleSlot(bar) and bar:IsMouseOver(LIP_REACH, -LIP_REACH, -LIP_REACH, LIP_REACH)
	local canMove = not ns.db.locked and not InCombatLockdown()
	bar.lip:SetShown(bar.moving or (canMove and (ns.optionsOpen or near)) or false)
	bar:SetAlpha((not ns.db.hover or bar.moving or ns.optionsOpen or near) and 1 or 0)
end

local function LayoutLip(bar, size, vertical)
	local lip = bar.lip
	local length = math.max(16, math.floor(size * 0.7))
	lip:ClearAllPoints()
	if vertical then
		lip:SetSize(length, LIP_THICKNESS)
		lip:SetPoint("BOTTOM", bar, "TOP", 0, LIP_GAP)
	else
		lip:SetSize(LIP_THICKNESS, length)
		lip:SetPoint("RIGHT", bar, "LEFT", -LIP_GAP, 0)
	end
	for index, line in ipairs(lip.lines) do
		local offset = index == 1 and -1.5 or 1.5
		line:ClearAllPoints()
		line:SetPoint("CENTER", vertical and 0 or offset, vertical and offset or 0)
		line:SetSize(vertical and length - 8 or 1, vertical and 1 or length - 8)
	end
end

local function CreateLip(bar)
	local lip = CreateFrame("Frame", nil, bar)
	lip:EnableMouse(true)
	lip:RegisterForDrag("LeftButton")
	local background = lip:CreateTexture(nil, "BACKGROUND")
	background:SetAllPoints()
	background:SetColorTexture(0, 0, 0, 0.7)
	lip.lines = { lip:CreateTexture(nil, "ARTWORK"), lip:CreateTexture(nil, "ARTWORK") }
	local function SetLineColor(r, g, b)
		for _, line in ipairs(lip.lines) do
			line:SetColorTexture(r, g, b, 0.9)
		end
	end
	SetLineColor(0.6, 0.6, 0.6)
	lip:SetScript("OnEnter", function()
		SetLineColor(1, 0.82, 0)
	end)
	lip:SetScript("OnLeave", function()
		SetLineColor(0.6, 0.6, 0.6)
	end)
	lip:SetScript("OnDragStart", function()
		if not InCombatLockdown() then
			bar.moving = true
			bar:StartMoving()
		end
	end)
	lip:SetScript("OnDragStop", function()
		StopMoving(bar)
	end)
	lip:Hide()

	-- Polled instead of an invisible mouse area, which would block clicks on the game world.
	local watcher = CreateFrame("Frame", nil, bar)
	local elapsed = 0
	watcher:SetScript("OnUpdate", function(_, delta)
		elapsed = elapsed + delta
		if elapsed >= 0.1 then
			elapsed = 0
			UpdateHover(bar)
		end
	end)
	return lip
end

function ns.CreateBars()
	for index, info in ipairs(ns.BARS) do
		local bar = CreateFrame("Frame", nil, UIParent)
		bar.key = info.key
		bar:SetMovable(true)
		bar:SetClampedToScreen(true)
		bar:SetClampRectInsets(-LIP_THICKNESS - LIP_GAP, 0, LIP_THICKNESS + LIP_GAP, 0) -- keep the lip on screen
		bar.slots = {}
		for _, kind in ipairs(info.kinds) do
			slots[#slots + 1] = CreateSlot(bar, kind)
		end
		bar.lip = CreateLip(bar)
		bars[index] = bar
	end
end

-- Puts every slot on its own bar, or all of them on the first bar when the potions are attached.
local function AssignSlots()
	for _, bar in ipairs(bars) do
		bar.slots = {}
	end
	for _, slot in ipairs(slots) do
		local config = ns.db.bars[slot.home.key]
		local bar = ns.db.attach and bars[1] or slot.home
		slot.enabled = config.enabled and config.slots[slot.kind]
		slot:SetParent(bar)
		bar.slots[#bar.slots + 1] = slot
	end
end

-- Attached potions continue the line of the food and water, or start a second line (a square).
-- Returns the number of slots in the longest line.
local function LayoutSlots(bar, size, gap)
	local vertical = ns.db.bars[bar.key].vertical
	local newLine = ns.db.attach ~= (vertical and "vertical" or "horizontal")
	local step = size + gap
	local position, line, longest = 0, 0, 0
	local home
	for _, slot in ipairs(bar.slots) do
		if slot.enabled then
			if newLine and home and home ~= slot.home then
				position, line = 0, line + 1
			end
			home = slot.home
			local along, across = position * step, line * step
			slot:SetSize(size, size)
			slot:ClearAllPoints()
			slot:SetPoint("TOPLEFT", vertical and across or along, vertical and -along or -across)
			local font, _, flags = slot.count:GetFont()
			slot.count:SetFont(font, math.max(9, math.floor(size * 0.36)), flags)
			position = position + 1
			longest = math.max(longest, position)
		end
	end
	local length, thickness = math.max(longest, 1) * step - gap, (line + 1) * step - gap
	bar:SetSize(vertical and thickness or length, vertical and length or thickness)
	return longest
end

-- Size, gap, direction, slots, position and visibility. Out of combat only.
function ns.ApplySettings()
	if InCombatLockdown() then
		return
	end
	AssignSlots()
	local size, gap = ns.db.size, ns.db.gap
	for _, bar in ipairs(bars) do
		local longest = LayoutSlots(bar, size, gap)
		LayoutLip(bar, size, ns.db.bars[bar.key].vertical)
		bar:SetShown(longest > 0)
		Place(bar)
	end
	ns.Refresh()
	for _, bar in ipairs(bars) do
		UpdateHover(bar)
	end
end

function ns.StopMovingBars()
	for _, bar in ipairs(bars) do
		StopMoving(bar)
	end
end

-- While the options are open, empty slots, hidden bars and the lips are visible.
function ns.SetOptionsOpen(open)
	ns.optionsOpen = open
	ns.Refresh()
	for _, bar in ipairs(bars) do
		UpdateHover(bar)
	end
end
