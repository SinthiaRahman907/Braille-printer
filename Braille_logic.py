from stepper_control import BraillePrinter

# ── Braille dimensions (mm) ───────────────────────────────────────────────────
DOT_SPACING  = 2.5
CELL_SPACING = 6.0
LINE_SPACING = 10.0
MARGIN_X     = 5.0
MARGIN_Y     = 5.0

# ── Grade-1 English Braille map ───────────────────────────────────────────────
braille_map = {
    "a":[1],   "b":[1,2], "c":[1,4],   "d":[1,4,5], "e":[1,5],
    "f":[1,2,4],"g":[1,2,4,5],"h":[1,2,5],"i":[2,4],"j":[2,4,5],
    "k":[1,3], "l":[1,2,3],"m":[1,3,4],"n":[1,3,4,5],"o":[1,3,5],
    "p":[1,2,3,4],"q":[1,2,3,4,5],"r":[1,2,3,5],"s":[2,3,4],"t":[2,3,4,5],
    "u":[1,3,6],"v":[1,2,3,6],"w":[2,4,5,6],"x":[1,3,4,6],"y":[1,3,4,5,6],
    "z":[1,3,5,6]," ":[]
}

def print_braille_text(printer: BraillePrinter, text: str):
    """Translate and emboss `text`."""
    printer.absolute_mode = True
    # start at margin
    printer.move(x_target=MARGIN_X, y_target=MARGIN_Y)
    printer.x_pos = MARGIN_X
    printer.y_pos = MARGIN_Y

    lines = text.splitlines()
    for li, line in enumerate(lines):
        if li > 0:
            new_y = printer.y_pos + LINE_SPACING
            printer.move(x_target=MARGIN_X, y_target=new_y)
            printer.x_pos = MARGIN_X
            printer.y_pos = new_y

        for ch in line.lower():
            if ch not in braille_map:
                continue
            dots = braille_map[ch]
            base_x, base_y = printer.x_pos, printer.y_pos

            for dot in dots:
                if dot == 1: dx,dy = 0,0
                elif dot == 2: dx,dy = 0,DOT_SPACING
                elif dot == 3: dx,dy = 0,2*DOT_SPACING
                elif dot == 4: dx,dy = DOT_SPACING,0
                elif dot == 5: dx,dy = DOT_SPACING,DOT_SPACING
                elif dot == 6: dx,dy = DOT_SPACING,2*DOT_SPACING
                else: continue

                printer.move(
                    x_target=base_x+dx,
                    y_target=base_y+dy,
                    feed=300.0
                )
                printer.punch_dot(duration=0.1)

            # advance to next cell
            new_x = printer.x_pos + CELL_SPACING
            printer.move(x_target=new_x, y_target=printer.y_pos)
            printer.x_pos = new_x
