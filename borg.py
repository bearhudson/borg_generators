import argparse
import random
import sys
import cadquery as cq

# ================================================
# Borg Surface - Interactive CAD Generator
# ================================================


def get_user_inputs():
    """Prompt the user for dimensions, wall thickness, and seed with defaults."""
    print("\n--- Borg Surface Generator Configuration ---")

    # Box X
    try:
        val = input("Enter X dimension in mm [Default: 156]: ").strip()
        box_x = float(val) if val else 156.0
    except ValueError:
        print("Invalid input; defaulting X to 156 mm.")
        box_x = 156.0

    # Box Y
    try:
        val = input("Enter Y dimension in mm [Default: 126]: ").strip()
        box_y = float(val) if val else 126.0
    except ValueError:
        print("Invalid input; defaulting Y to 126 mm.")
        box_y = 126.0

    # Base Z
    try:
        val = input(
            "Enter Base Thickness (Z) in mm [Default: 10.0]: "
        ).strip()
        base_z = float(val) if val else 10.0
    except ValueError:
        print("Invalid input; defaulting Z to 10.0 mm.")
        base_z = 10.0

    # Minimum Wall Thickness
    try:
        val = input(
            "Enter Minimum Wall/Feature Width in mm [Default: 0.45]: "
        ).strip()
        min_w = float(val) if val else 0.45
    except ValueError:
        print("Invalid input; defaulting min_w to 0.45 mm.")
        min_w = 0.45

    # Random Seed
    try:
        val = input("Enter Random Seed [Default: 404]: ").strip()
        seed = int(val) if val else 404
    except ValueError:
        print("Invalid input; defaulting seed to 404.")
        seed = 404

    print(
        f"\nConfiguration: Size = {box_x}x{box_y}x{base_z}mm | Min Wall = {min_w}mm | Seed = {seed}\n"
    )
    return box_x, box_y, base_z, min_w, seed


# Get user inputs
box_x, box_y, base_z, min_w, seed = get_user_inputs()
gap = 0.6  # Clearance gap between packed objects

# ------------------------------------------------
# Greeble Component Builders
# ------------------------------------------------


def greeble_large_bay(w, l, h):
    bay = cq.Workplane("XY").box(w, l, h, centered=(False, False, False))

    if w > min_w * 4 and l > min_w * 4:
        cavity = (
            cq.Workplane("XY")
            .workplane(offset=h * 0.4)
            .moveTo(min_w * 2, min_w * 2)
            .rect(w - min_w * 4, l - min_w * 4, centered=False)
            .extrude(h)
        )
        bay = bay.cut(cavity)

    island = (
        cq.Workplane("XY")
        .workplane(offset=h * 0.2)
        .moveTo(w * 0.2, l * 0.2)
        .box(w * 0.6, l * 0.6, h * 0.6, centered=(False, False, False))
    )

    return bay.union(island)


def greeble_medium_stepped(w, l, h):
    base = cq.Workplane("XY").box(w, l, h * 0.5, centered=(False, False, False))

    step1 = (
        cq.Workplane("XY")
        .workplane(offset=h * 0.5)
        .moveTo(w * 0.2, l * 0.2)
        .box(w * 0.6, l * 0.6, h * 0.3, centered=(False, False, False))
    )

    step2 = (
        cq.Workplane("XY")
        .workplane(offset=h * 0.8)
        .moveTo(w * 0.2 + w * 0.15, l * 0.2 + l * 0.15)
        .box(w * 0.3, l * 0.3, h * 0.4, centered=(False, False, False))
    )

    return base.union(step1).union(step2)


def greeble_medium_vent(w, l, h):
    base = cq.Workplane("XY").box(w, l, h * 0.3, centered=(False, False, False))

    rib_w = max(min_w, 0.8)
    rib_gap = max(min_w, 0.8)
    num_ribs = int(max(1, (l - rib_gap) // (rib_w + rib_gap)))

    ribs = base
    for r in range(num_ribs):
        y_pos = rib_gap + r * (rib_w + rib_gap)
        rib = (
            cq.Workplane("XY")
            .workplane(offset=h * 0.3)
            .moveTo(min_w, y_pos)
            .box(w - min_w * 2, rib_w, h * 0.7, centered=(False, False, False))
        )
        ribs = ribs.union(rib)

    return ribs


def greeble_small_node(w, l, h):
    base = cq.Workplane("XY").box(w, l, h, centered=(False, False, False))
    if w > min_w * 3 and l > min_w * 3:
        cap = (
            cq.Workplane("XY")
            .workplane(offset=h)
            .moveTo(min_w, min_w)
            .box(
                w - min_w * 2,
                l - min_w * 2,
                h * 0.3,
                centered=(False, False, False),
            )
        )
        base = base.union(cap)
    return base


def greeble_small_recess(w, l, h):
    base = cq.Workplane("XY").box(w, l, h, centered=(False, False, False))
    if w > min_w * 3 and l > min_w * 3:
        cutout = (
            cq.Workplane("XY")
            .workplane(offset=h * 0.5)
            .moveTo(min_w, min_w)
            .rect(w - min_w * 2, l - min_w * 2, centered=False)
            .extrude(h)
        )
        base = base.cut(cutout)
    return base


# ------------------------------------------------
# Spatial Greedy Packing Logic
# ------------------------------------------------

try:
    base_box = cq.Workplane("XY").box(
        box_x, box_y, base_z, centered=(False, False, False)
    )
except Exception as e:
    print(f"Error creating base plate: {e}")
    sys.exit(1)

step = 6.0
cols = int(box_x // step)
rows = int(box_y // step)

raw_shapes = []
failed_count = 0

for c in range(cols):
    for r in range(rows):
        p_seed = seed + c * 37 + r * 91
        rng = random.Random(p_seed)

        if rng.random() > 0.35:
            x = c * step
            y = r * step

            size_cat = int(rng.uniform(0, 3))

            if size_cat == 0:
                w_raw = rng.uniform(20, 36)
                l_raw = rng.uniform(20, 36)
            elif size_cat == 1:
                w_raw = rng.uniform(10, 18)
                l_raw = rng.uniform(10, 18)
            else:
                w_raw = rng.uniform(3, 8)
                l_raw = rng.uniform(3, 8)

            w = max(min_w * 3, min(w_raw, box_x - x - gap))
            l = max(min_w * 3, min(l_raw, box_y - y - gap))
            h = rng.uniform(1.5, 6.5)

            if w > min_w * 2 and l > min_w * 2:
                eff_w = w - gap
                eff_l = l - gap

                try:
                    if size_cat == 0:
                        greeble = greeble_large_bay(eff_w, eff_l, h)
                    elif size_cat == 1:
                        greeble = (
                            greeble_medium_stepped(eff_w, eff_l, h)
                            if p_seed % 2 == 0
                            else greeble_medium_vent(eff_w, eff_l, h)
                        )
                    else:
                        greeble = (
                            greeble_small_node(eff_w, eff_l, h)
                            if p_seed % 2 == 0
                            else greeble_small_recess(eff_w, eff_l, h)
                        )

                    translated_greeble = greeble.translate((x, y, base_z))
                    raw_shapes.append(translated_greeble.val())
                except Exception as e:
                    failed_count += 1

if failed_count > 0:
    print(f"Skipped {failed_count} problematic greebles.")

# ------------------------------------------------
# Fast Compound Assembly & STEP Export
# ------------------------------------------------

output_filename = f"borg_surface_{int(box_x)}x{int(box_y)}_seed{seed}.step"

try:
    if raw_shapes:
        compound_shape = cq.Compound.makeCompound(raw_shapes)
        greeble_compound = cq.Workplane("XY").newObject([compound_shape])
        assembly = base_box.union(greeble_compound)
    else:
        assembly = base_box

    cq.exporters.export(assembly, output_filename)
    print(f"Successfully exported '{output_filename}'!")

except Exception as e:
    print(f"Error exporting assembly: {e}")
    sys.exit(1)
