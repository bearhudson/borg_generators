import argparse
import random
import sys
import cadquery as cq

# ================================================
# Borg Surface - Multi-Side CAD Generator
# (With L-Shaped Corner Wrap-Arounds)
# ================================================


def get_user_inputs():
    """Prompt the user for dimensions, wall thickness, sides, and seed with defaults."""
    print("\n--- Borg Surface Generator Configuration ---")

    try:
        val = input("Enter X dimension in mm [Default: 156]: ").strip()
        box_x = float(val) if val else 156.0
    except ValueError:
        box_x = 156.0

    try:
        val = input("Enter Y dimension in mm [Default: 126]: ").strip()
        box_y = float(val) if val else 126.0
    except ValueError:
        box_y = 126.0

    try:
        val = input("Enter Base Thickness (Z) in mm [Default: 10.0]: ").strip()
        base_z = float(val) if val else 10.0
    except ValueError:
        base_z = 10.0

    try:
        val = input("Enter Number of Sides to Greeble (1 to 6) [Default: 1]: ").strip()
        num_sides = int(val) if val else 1
        num_sides = max(1, min(6, num_sides))
    except ValueError:
        num_sides = 1

    try:
        val = input(
            "Enter Minimum Wall/Feature Width in mm [Default: 0.45]: "
        ).strip()
        min_w = float(val) if val else 0.45
    except ValueError:
        min_w = 0.45

    try:
        val = input("Enter Random Seed [Default: 404]: ").strip()
        seed = int(val) if val else 404
    except ValueError:
        seed = 404

    print(
        f"\nConfiguration: Size = {box_x}x{box_y}x{base_z}mm | Sides = {num_sides} | Min Wall = {min_w}mm | Seed = {seed}\n"
    )
    return box_x, box_y, base_z, num_sides, min_w, seed


# Get user inputs
box_x, box_y, base_z, num_sides, min_w, seed = get_user_inputs()
gap = 0.6  # Clearance gap between packed objects

# ------------------------------------------------
# Greeble Component Builders
# ------------------------------------------------


def greeble_corner_l_bracket(w, l, h, leg_down=6.0):
    """Constructs a 90-degree L-bracket that wraps around an outer edge."""
    thickness = max(min_w, 1.2)

    # Top leg on the main face
    top_leg = cq.Workplane("XY").box(w, l, h, centered=(False, False, False))

    # Downward wrap leg over the adjacent face
    wrap_leg = (
        cq.Workplane("XY")
        .workplane(offset=-leg_down)
        .moveTo(0, l - thickness)
        .box(w, thickness, leg_down + h, centered=(False, False, False))
    )

    # Internal detail cutout on the top face
    if w > min_w * 4 and l > min_w * 4:
        recess = (
            cq.Workplane("XY")
            .workplane(offset=h * 0.5)
            .moveTo(min_w * 2, min_w * 2)
            .rect(w - min_w * 4, l - min_w * 4, centered=False)
            .extrude(h)
        )
        return top_leg.union(wrap_leg).cut(recess)

    return top_leg.union(wrap_leg)


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
# Modular Greeble Generator with Edge Detection
# ------------------------------------------------


def generate_side_greebles(dim_u, dim_v, side_seed):
    """Generates packed greebles, placing L-shaped wrap elements near edges."""
    step = 6.0
    cols = int(dim_u // step)
    rows = int(dim_v // step)
    edge_margin = 12.0  # Distance threshold to detect outer boundary edges

    shapes = []
    for c in range(cols):
        for r in range(rows):
            p_seed = side_seed + c * 37 + r * 91
            rng = random.Random(p_seed)

            if rng.random() > 0.35:
                u = c * step
                v = r * step

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

                w = max(min_w * 3, min(w_raw, dim_u - u - gap))
                l = max(min_w * 3, min(l_raw, dim_v - v - gap))
                h = rng.uniform(1.5, 6.5)

                # Check if this placement touches an outer edge
                is_edge = (
                    (u + w >= dim_u - edge_margin)
                    or (v + l >= dim_v - edge_margin)
                    or (u <= edge_margin)
                    or (v <= edge_margin)
                )

                if w > min_w * 2 and l > min_w * 2:
                    eff_w = w - gap
                    eff_l = l - gap

                    try:
                        # Use L-bracket wrap if at a corner/edge
                        if is_edge and rng.random() > 0.4:
                            greeble = greeble_corner_l_bracket(
                                eff_w, eff_l, h, leg_down=rng.uniform(4.0, 8.0)
                            )
                        elif size_cat == 0:
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

                        translated = greeble.translate((u, v, 0))
                        shapes.append(translated.val())
                    except Exception:
                        pass
    return shapes


# ------------------------------------------------
# Multi-Face Assembly Logic
# ------------------------------------------------

try:
    base_box = cq.Workplane("XY").box(
        box_x, box_y, base_z, centered=(False, False, False)
    )
except Exception as e:
    print(f"Error creating base plate: {e}")
    sys.exit(1)

# Plane Definitions: Explicit Local Workplane Orientations
face_planes = [
    # Side 1: Top (+Z)
    (box_x, box_y, (0, 0, base_z), (1, 0, 0), (0, 0, 1)),
    # Side 2: Bottom (-Z)
    (box_x, box_y, (0, box_y, 0), (1, 0, 0), (0, 0, -1)),
    # Side 3: Front (-Y)
    (box_x, base_z, (0, 0, 0), (1, 0, 0), (0, -1, 0)),
    # Side 4: Back (+Y)
    (box_x, base_z, (box_x, box_y, 0), (-1, 0, 0), (0, 1, 0)),
    # Side 5: Left (-X)
    (box_y, base_z, (0, box_y, 0), (0, -1, 0), (-1, 0, 0)),
    # Side 6: Right (+X)
    (box_y, base_z, (box_x, 0, 0), (0, 1, 0), (1, 0, 0)),
]

all_side_shapes = []

for idx in range(num_sides):
    u_dim, v_dim, origin, x_dir, normal = face_planes[idx]
    side_seed = seed + idx * 1000

    raw_side_shapes = generate_side_greebles(u_dim, v_dim, side_seed)

    if raw_side_shapes:
        face_plane = cq.Workplane(
            cq.Plane(origin=origin, xDir=x_dir, normal=normal)
        )
        side_compound = cq.Compound.makeCompound(raw_side_shapes)
        oriented_greeble = face_plane.eachpoint(
            lambda loc: side_compound.moved(loc), useLocalCoordinates=True
        )
        all_side_shapes.append(oriented_greeble.val())

# ------------------------------------------------
# Fast Compound Assembly & STEP Export
# ------------------------------------------------

output_filename = (
    f"borg_surface_{int(box_x)}x{int(box_y)}_{num_sides}sides_seed{seed}.step"
)

try:
    if all_side_shapes:
        compound_shape = cq.Compound.makeCompound(all_side_shapes)
        greeble_compound = cq.Workplane("XY").newObject([compound_shape])
        assembly = base_box.union(greeble_compound)
    else:
        assembly = base_box

    cq.exporters.export(assembly, output_filename)
    print(
        f"Successfully exported '{output_filename}' ({num_sides} side(s) generated)!"
    )

except Exception as e:
    print(f"Error exporting assembly: {e}")
    sys.exit(1)
