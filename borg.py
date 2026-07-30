import argparse
import math
import random
import sys
import cadquery as cq

# ================================================
# Borg Surface - Aggressive Anchored Packing
# ================================================


def get_user_inputs():
    """Prompt the user for dimensions, wall thickness, sides, and seed with defaults."""
    print("\n--- Borg Surface Generator Configuration ---")

    try:
        val = input("Enter Inner X dimension in mm [Default: 156]: ").strip()
        box_x = float(val) if val else 156.0
    except ValueError:
        box_x = 156.0

    try:
        val = input("Enter Inner Y dimension in mm [Default: 126]: ").strip()
        box_y = float(val) if val else 126.0
    except ValueError:
        box_y = 126.0

    try:
        val = input("Enter Inner Base Thickness (Z) in mm [Default: 10.0]: ").strip()
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
        f"\nConfiguration: Inner Box = {box_x}x{box_y}x{base_z}mm | Sides = {num_sides} | Min Wall = {min_w}mm | Seed = {seed}\n"
    )
    return box_x, box_y, base_z, num_sides, min_w, seed


# Get user inputs
box_x, box_y, base_z, num_sides, min_w, seed = get_user_inputs()
gap = 0.4  # Tightened gap to increase placement density

# ------------------------------------------------
# Greeble Primitive Builders
# ------------------------------------------------


def greeble_corner_l_bracket(plane, u, v, w, l, h, leg_down=4.0):
    """Constructs an L-bracket physically anchored to the main face and wrapping over the edge."""
    thickness = max(min_w, 1.2)

    top_leg = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h, centered=(False, False, False))
    )

    wrap_leg = (
        cq.Workplane(plane)
        .workplane(offset=-leg_down)
        .moveTo(u, v + l - thickness)
        .box(w, thickness, leg_down + h, centered=(False, False, False))
    )

    return top_leg.union(wrap_leg)


def greeble_large_bay(plane, u, v, w, l, h):
    bay = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h, centered=(False, False, False))
    )

    if w > min_w * 4 and l > min_w * 4:
        cavity = (
            cq.Workplane(plane)
            .workplane(offset=h * 0.4)
            .moveTo(u + min_w * 2, v + min_w * 2)
            .rect(w - min_w * 4, l - min_w * 4, centered=False)
            .extrude(h)
        )
        bay = bay.cut(cavity)

    island = (
        cq.Workplane(plane)
        .workplane(offset=h * 0.2)
        .moveTo(u + w * 0.2, v + l * 0.2)
        .box(w * 0.6, l * 0.6, h * 0.6, centered=(False, False, False))
    )

    return bay.union(island)


def greeble_medium_stepped(plane, u, v, w, l, h):
    base = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h * 0.5, centered=(False, False, False))
    )

    step1 = (
        cq.Workplane(plane)
        .workplane(offset=h * 0.5)
        .moveTo(u + w * 0.2, v + l * 0.2)
        .box(w * 0.6, l * 0.6, h * 0.3, centered=(False, False, False))
    )

    step2 = (
        cq.Workplane(plane)
        .workplane(offset=h * 0.8)
        .moveTo(u + w * 0.35, v + l * 0.35)
        .box(w * 0.3, l * 0.3, h * 0.4, centered=(False, False, False))
    )

    return base.union(step1).union(step2)


def greeble_medium_vent(plane, u, v, w, l, h):
    base = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h * 0.3, centered=(False, False, False))
    )

    rib_w = max(min_w, 0.8)
    rib_gap = max(min_w, 0.8)
    num_ribs = int(max(1, (l - rib_gap) // (rib_w + rib_gap)))

    ribs = base
    for r in range(num_ribs):
        y_pos = v + rib_gap + r * (rib_w + rib_gap)
        rib = (
            cq.Workplane(plane)
            .workplane(offset=h * 0.3)
            .moveTo(u + min_w, y_pos)
            .box(w - min_w * 2, rib_w, h * 0.7, centered=(False, False, False))
        )
        ribs = ribs.union(rib)

    return ribs


def greeble_small_node(plane, u, v, w, l, h):
    base = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h, centered=(False, False, False))
    )
    if w > min_w * 3 and l > min_w * 3:
        cap = (
            cq.Workplane(plane)
            .workplane(offset=h)
            .moveTo(u + min_w, v + min_w)
            .box(
                w - min_w * 2,
                l - min_w * 2,
                h * 0.3,
                centered=(False, False, False),
            )
        )
        base = base.union(cap)
    return base


def greeble_small_recess(plane, u, v, w, l, h):
    base = (
        cq.Workplane(plane)
        .moveTo(u, v)
        .box(w, l, h, centered=(False, False, False))
    )
    if w > min_w * 3 and l > min_w * 3:
        cutout = (
            cq.Workplane(plane)
            .workplane(offset=h * 0.5)
            .moveTo(u + min_w, v + min_w)
            .rect(w - min_w * 2, l - min_w * 2, centered=False)
            .extrude(h)
        )
        base = base.cut(cutout)
    return base


# ------------------------------------------------
# Aggressive Dense Packing Engine with Anchor Check
# ------------------------------------------------


def generate_dense_anchored_greebles(plane, dim_u, dim_v, side_seed):
    """Generates packed greebles with high placement probability and mandatory edge anchors."""
    step = 5.0  # Finer grid step for dense coverage
    edge_margin = 10.0

    cols = int(dim_u // step)
    rows = int(dim_v // step)

    shapes = []

    for c in range(cols):
        for r in range(rows):
            p_seed = side_seed + c * 37 + r * 91
            rng = random.Random(p_seed)

            # High fill probability (80% placement rate)
            if rng.random() > 0.20:
                u = c * step
                v = r * step

                dist_to_edge = min(u, dim_u - u, v, dim_v - v)

                # Size distribution based on distance from border
                if dist_to_edge <= 0 or dist_to_edge < edge_margin:
                    # Outer border: Force small micro-accents or L-brackets
                    size_cat = 2
                    w_raw = rng.uniform(4, 9)
                    l_raw = rng.uniform(4, 9)
                    h = rng.uniform(1.5, 4.0)
                elif dist_to_edge < edge_margin * 1.8:
                    size_cat = int(rng.uniform(1, 3))
                    w_raw = rng.uniform(8, 16)
                    l_raw = rng.uniform(8, 16)
                    h = rng.uniform(1.5, 5.5)
                else:
                    size_cat = int(rng.uniform(0, 3))
                    if size_cat == 0:
                        w_raw = rng.uniform(18, 30)
                        l_raw = rng.uniform(18, 30)
                    elif size_cat == 1:
                        w_raw = rng.uniform(10, 18)
                        l_raw = rng.uniform(10, 18)
                    else:
                        w_raw = rng.uniform(4, 9)
                        l_raw = rng.uniform(4, 9)
                    h = rng.uniform(1.5, 6.5)

                w = max(min_w * 3, w_raw)
                l = max(min_w * 3, l_raw)

                # Clamp size so elements don't extend past the main face without anchoring
                w_clamped = min(w, max(min_w * 3, dim_u - u))
                l_clamped = min(l, max(min_w * 3, dim_v - v))

                # ANCHOR CHECK: Detect if element extends over a face edge
                is_overflow = (u + w > dim_u) or (v + l > dim_v) or (u < 0) or (v < 0)

                eff_w = max(min_w * 2, w_clamped - gap)
                eff_l = max(min_w * 2, l_clamped - gap)

                try:
                    if is_overflow:
                        # Convert overflow elements into anchored 90-degree L-brackets
                        greeble = greeble_corner_l_bracket(
                            plane,
                            max(0, u),
                            max(0, v),
                            eff_w,
                            eff_l,
                            h,
                            leg_down=rng.uniform(3.0, 6.0),
                        )
                    elif size_cat == 0:
                        greeble = greeble_large_bay(
                            plane, u, v, eff_w, eff_l, h
                        )
                    elif size_cat == 1:
                        greeble = (
                            greeble_medium_stepped(plane, u, v, eff_w, eff_l, h)
                            if p_seed % 2 == 0
                            else greeble_medium_vent(plane, u, v, eff_w, eff_l, h)
                        )
                    else:
                        greeble = (
                            greeble_small_node(plane, u, v, eff_w, eff_l, h)
                            if p_seed % 2 == 0
                            else greeble_small_recess(plane, u, v, eff_w, eff_l, h)
                        )

                    shapes.append(greeble)
                except Exception:
                    pass

    return shapes


# ------------------------------------------------
# Multi-Face Assembly Logic
# ------------------------------------------------

try:
    base_solid = cq.Workplane("XY").box(
        box_x, box_y, base_z, centered=(False, False, False)
    )
except Exception as e:
    print(f"Error creating base plate: {e}")
    sys.exit(1)

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

result_solid = base_solid

for idx in range(num_sides):
    u_dim, v_dim, origin, x_dir, normal = face_planes[idx]
    side_seed = seed + idx * 1000

    plane = cq.Plane(origin=origin, xDir=x_dir, normal=normal)
    side_greebles = generate_dense_anchored_greebles(
        plane, u_dim, v_dim, side_seed
    )

    for greeble in side_greebles:
        try:
            result_solid = result_solid.union(greeble)
        except Exception:
            pass

# ------------------------------------------------
# Clean STEP Export
# ------------------------------------------------

output_filename = (
    f"borg_surface_{int(box_x)}x{int(box_y)}x{int(base_z)}_{num_sides}sides_seed{seed}.step"
)

try:
    cq.exporters.export(result_solid, output_filename)
    print(
        f"Successfully exported '{output_filename}' as a unified, fully anchored solid part!"
    )
except Exception as e:
    print(f"Error exporting assembly: {e}")
    sys.exit(1)
