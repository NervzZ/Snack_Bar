local _, ns = ...

local WIDTH, PADDING, COLUMN = 330, 20, 140
local NUMBER = "^%s*(%-?%d+%.?%d*)%s*$"

local options
local updates = {} -- functions that copy the saved settings into the controls

local function Update()
	for _, update in ipairs(updates) do
		update()
	end
end

local function Changed()
	Update()
	ns.ApplySettings()
end

-- Controls ------------------------------------------------------------------

local function CreateLabel(parent, font, text, x, y)
	local label = parent:CreateFontString(nil, "ARTWORK", font)
	label:SetPoint("TOPLEFT", x, y)
	label:SetText(text)
	return label
end

local function CreateCheckbox(parent, label, x, y, onClick)
	local check = CreateFrame("CheckButton", nil, parent, "UICheckButtonTemplate")
	check:SetSize(26, 26)
	check:SetPoint("TOPLEFT", x - 4, y)
	check.label = check.Text
	check.label:SetFontObject("GameFontHighlight")
	check.label:SetText(label)
	check:SetScript("OnClick", function(self)
		onClick(self:GetChecked() and true or false)
		Changed()
	end)
	return check
end

local function CreateRadio(parent, label, x, y, onClick)
	local radio = CreateFrame("CheckButton", nil, parent, "UIRadioButtonTemplate")
	radio:SetPoint("TOPLEFT", x + 1, y)
	radio.label = radio.text
	radio.label:SetFontObject("GameFontHighlight")
	radio.label:SetText(label)
	radio:SetScript("OnClick", function()
		onClick()
		Changed()
	end)
	return radio
end

local function Clamp(value, low, high)
	return math.max(low, math.min(high, value))
end

-- A number to type: Enter or a click elsewhere applies it, Escape restores the old one.
local function CreateField(parent, x, y, get, set)
	local field = CreateFrame("EditBox", nil, parent, "InputBoxTemplate")
	field:SetPoint("TOPLEFT", x, y)
	field:SetSize(46, 20)
	field:SetAutoFocus(false)
	field:SetMaxLetters(6)
	field:SetJustifyH("CENTER")
	function field.ShowValue()
		field:SetText(tostring(get()))
		field:SetCursorPosition(0)
	end
	field:SetScript("OnEnterPressed", field.ClearFocus)
	field:SetScript("OnEscapePressed", function()
		field.ShowValue()
		field:ClearFocus()
	end)
	field:HookScript("OnEditFocusLost", function()
		local value = tonumber((field:GetText():match(NUMBER)))
		if value and value ~= get() then
			set(math.floor(value + 0.5))
			Changed()
		end
		field.ShowValue()
	end)
	updates[#updates + 1] = field.ShowValue
	return field
end

local function CreateSlider(parent, label, y, key, low, high)
	CreateLabel(parent, "GameFontHighlight", label, PADDING + 1, y - 13)
	local field = CreateField(parent, PADDING + 244, y - 9, function()
		return ns.db[key]
	end, function(value)
		ns.db[key] = Clamp(value, low, high)
	end)
	local slider = CreateFrame("Frame", nil, parent, "MinimalSliderWithSteppersTemplate")
	slider:SetPoint("TOPLEFT", PADDING + 40, y)
	slider:SetWidth(190)
	slider:Init(ns.db[key], low, high, high - low)
	slider:RegisterCallback(MinimalSliderWithSteppersMixin.Event.OnValueChanged, function(_, value)
		local rounded = math.floor(value + 0.5)
		if rounded ~= ns.db[key] then
			ns.db[key] = rounded
			field.ShowValue()
			ns.ApplySettings()
		end
	end, slider)
	updates[#updates + 1] = function()
		slider:SetValue(ns.db[key])
	end
end

local function SetControlEnabled(control, enabled)
	control:SetEnabled(enabled)
	control.label:SetAlpha(enabled and 1 or 0.4)
end

-- The offset of the bar's top left corner from the middle of the screen.
local function CreatePositionField(parent, label, x, y, labelWidth, config, axis, GetScreenSize)
	local field = CreateField(parent, x + labelWidth, y, function()
		return config[axis]
	end, function(value)
		local limit = math.floor(GetScreenSize(UIParent) / 2)
		config[axis] = Clamp(value, -limit, limit)
	end)
	field.label = CreateLabel(parent, "GameFontHighlight", label, x + 1, y - 4)
	return field
end

-- Sections ------------------------------------------------------------------

-- Builds one bar's controls from y downward and returns the next free y.
local function CreateBarSection(parent, info, y)
	local config = ns.db.bars[info.key]
	local isPotion = info.key == "potion"
	local show, attach, stones

	CreateLabel(parent, "GameFontNormalLarge", info.label, PADDING, y)
	y = y - 26

	if isPotion then
		show = CreateCheckbox(parent, "Show potions", PADDING, y, function(checked)
			config.enabled = checked
		end)
		y = y - 32
		attach = {
			[false] = CreateRadio(parent, "Separate bar", PADDING, y, function()
				ns.db.attach = false
			end),
			horizontal = CreateRadio(parent, "Attach horizontally", PADDING, y - 24, function()
				ns.db.attach = "horizontal"
			end),
			vertical = CreateRadio(parent, "Attach vertically", PADDING + COLUMN, y - 24, function()
				ns.db.attach = "vertical"
			end),
		}
		y = y - 46
	end

	local checks = {}
	for index, kind in ipairs(info.kinds) do
		checks[kind] = CreateCheckbox(parent, ns.KIND_LABELS[kind], PADDING + (index - 1) * COLUMN, y, function(checked)
			config.slots[kind] = checked
		end)
	end
	y = y - 34

	if isPotion then
		stones = CreateCheckbox(parent, "Healthstones as health potions", PADDING, y + 6, function(checked)
			ns.db.healthstones = checked
		end)
		y = y - 28
	end

	local horizontal = CreateRadio(parent, "Horizontal", PADDING, y, function()
		config.vertical = false
	end)
	local vertical = CreateRadio(parent, "Vertical", PADDING + COLUMN, y, function()
		config.vertical = true
	end)
	y = y - 26

	local positions = {
		CreatePositionField(parent, "Position X", PADDING, y, 72, config, "x", UIParent.GetWidth),
		CreatePositionField(parent, "Y", PADDING + COLUMN, y, 22, config, "y", UIParent.GetHeight),
	}
	y = y - 38

	updates[#updates + 1] = function()
		-- Attached potions follow the direction and the place of the bar they are on.
		local attached = isPotion and ns.db.attach
		local direction = attached and ns.db.bars.main or config
		horizontal:SetChecked(not direction.vertical)
		vertical:SetChecked(direction.vertical)
		SetControlEnabled(horizontal, config.enabled and not attached)
		SetControlEnabled(vertical, config.enabled and not attached)
		for _, field in ipairs(positions) do
			SetControlEnabled(field, config.enabled and not attached)
			field:SetAlpha(config.enabled and not attached and 1 or 0.4)
		end
		for kind, check in pairs(checks) do
			check:SetChecked(config.slots[kind])
			SetControlEnabled(check, config.enabled)
		end
		if isPotion then
			show:SetChecked(config.enabled)
			for value, radio in pairs(attach) do
				radio:SetChecked(ns.db.attach == value)
				SetControlEnabled(radio, config.enabled)
			end
			stones:SetChecked(ns.db.healthstones)
			SetControlEnabled(stones, config.enabled and config.slots.health)
		end
	end
	return y
end

local function CreateOptions()
	local frame = CreateFrame("Frame", "Snack_BarOptions", UIParent, "BasicFrameTemplateWithInset")
	frame:Hide()
	frame:SetPoint("CENTER", -340, 40)
	frame:SetFrameStrata("DIALOG")
	frame:SetClampedToScreen(true)
	frame:SetMovable(true)
	frame:EnableMouse(true)
	frame:RegisterForDrag("LeftButton")
	frame:SetScript("OnDragStart", frame.StartMoving)
	frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
	frame.TitleText:SetText("Snack Bar")
	tinsert(UISpecialFrames, "Snack_BarOptions") -- closes with Escape

	local y = -40
	for _, info in ipairs(ns.BARS) do
		y = CreateBarSection(frame, info, y)
	end
	CreateLabel(frame, "GameFontNormalLarge", "Both bars", PADDING, y)
	CreateSlider(frame, "Size", y - 22, "size", 20, 80)
	CreateSlider(frame, "Gap", y - 56, "gap", 0, 30)
	local hover = CreateCheckbox(frame, "Show only on mouse hover", PADDING, y - 96, function(checked)
		ns.db.hover = checked
	end)
	local lock = CreateCheckbox(frame, "Lock bars", PADDING, y - 122, function(checked)
		ns.db.locked = checked
	end)
	y = y - 162

	frame.hint = CreateLabel(frame, "GameFontNormalSmall", "Drag a bar by its tab to move it.", PADDING, y)
	updates[#updates + 1] = function()
		hover:SetChecked(ns.db.hover)
		lock:SetChecked(ns.db.locked)
		frame.hint:SetShown(not ns.db.locked)
	end
	frame:SetSize(WIDTH, 32 - y)

	frame:SetScript("OnShow", function()
		Update()
		ns.SetOptionsOpen(true)
	end)
	frame:SetScript("OnHide", function()
		ns.SetOptionsOpen(false)
	end)
	return frame
end

ns.UpdateOptions = Update

-- Combat starts: a number that is still being typed is dropped.
function ns.CloseOptions()
	if options then
		Update()
		options:Hide()
	end
end

SLASH_SNACK_BAR1 = "/snack"
SlashCmdList.SNACK_BAR = function()
	if InCombatLockdown() then
		print("Snack Bar: the options are not available in combat.")
		return
	end
	options = options or CreateOptions()
	options:SetShown(not options:IsShown())
end
