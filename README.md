# Snack Bar

Clickable slots that always show the best food and water in your bags, and your best health and mana potions if you want them. Made for WoW Forever.

## What it does

- **Always the best item.** Each slot shows the item in your bags that restores the most and that you can use at your level. Between equal items the cheapest goes first, so conjured food and water are used before bought ones.
- **Saves your special food.** Food that gives a buff, combined potions and potions with side effects are only used when nothing else is left.
- **Optional potions.** The health and mana potion slots are off by default. When you carry fewer than five of your best potion, the same button also holds the next best ones, so it keeps working during a fight.
- **Knows where items work.** Battleground food and potions only show up where they can be used.
- **Stays out of the way.** Empty slots are hidden, and the bars can be set to show only on mouse hover.

The game does not allow addons to change buttons in combat. If you loot better food during a fight, the slot switches to it when the fight ends.

## Options

Type `/snack` to choose:

- which slots are shown
- potions on their own bar, or attached to the food and water bar in a line or a square
- horizontal or vertical
- size, gap and position, with numbers you can type
- show only on mouse hover
- lock the bars

To move a bar, bring the mouse close to it and drag the small tab that appears.

Settings are saved per character. Items are recognized in every client language; the options window is in English.

Healthstones, mana gems and bandages are not included.

## Development

`addon/Snack_Bar` is the addon folder. The item data in `Data.lua` is generated from the game client's tables:

    python tools/build_data.py 1.60.1.71037

The offline tests need the tables downloaded by that script and `pip install lupa`:

    python tools/test_snackbar.py

## License

MIT, see [LICENSE](LICENSE).
