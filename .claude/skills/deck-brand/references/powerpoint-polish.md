# Polishing a template in PowerPoint

Give these steps to the user. They work in PowerPoint for Mac and Windows.

1. Open `template.potx` with File > Open, not by double-clicking. Double-clicking a `.potx`
   starts a new deck from it instead of editing the template.
2. View > Slide Master. The top slide is the master; the slides under it are the layouts.
3. **Theme fonts and colors:** Slide Master tab > Fonts and Colors > Customize. Change them here,
   never on individual text boxes, so every placeholder inherits them.
4. **Master elements:** logo, footer, page number and background go on the master or on a
   layout, never on a slide.
5. **Layouts:** keep the layout names the brand's `tokens.yaml` uses. Renaming a layout breaks
   the mapping until `tokens.yaml` is updated.
6. **Placeholders:** every slot the engine fills must be a placeholder (Insert Placeholder), not
   a text box. Use Picture placeholders for images, Chart and Table placeholders for those.
7. **Each placeholder:** set size, weight, color, line spacing and bullet style per level. Turn
   autofit off (Format Shape > Text Options > Do not Autofit); budgets handle overflow.
8. Save with File > Save As > PowerPoint Template (.potx), over the original.

Then run `deck-builder brand check <slug>`. If it reports a layout or placeholder mismatch,
`deck-builder inspect template.potx --yaml` shows the mapping to update in `tokens.yaml`.
