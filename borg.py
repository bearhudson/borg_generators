import random
import cadquery as cq

# ================================================
# Borg Surface - Mixed-Scale Greedy Packing
# ================================================

inch = 25.4
box_x = 156
box_y = 126
base_z = 10.0  # 10 mm base thickness

seed = 404
min_w = 0.45  # Minimum printable wall/feature width (mm)
gap = 0.6  # Clearance gap between packed objects

# ------------------------------------------------
# Greeble Component Builders
# (Each returns a cq.Workplane solid at relative 0,0,0)
# ------------------------------------------------


def greeble_large_bay(w, l, h):
    # Base box
    bay = cq.Workplane("XY").box(w, l, h, centered=(False, False, False))

    # Cut cavity if wide enough
    if w > min_w * 4 and l > min_w * 4:
        cavity = (
            cq.Workplane("XY")
            .workplane(offset=h * 0.4)
            .moveTo(min_w * 2, min_w * 2)
            .rect(w - min_w * 4, l - min_w * 4, centered=False)
            .extrude(h)
        )
        bay = bay.cut(cavity)

    # Raised internal island
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

# 1. Base Box
assembly = cq.Workplane("XY").box(
    box_x, box_y, base_z, centered=(False, False, False)
)

step = 6.0
cols = int(box_x // step)
rows = int(box_y // step)

# Collect all greebles to union them efficiently
greeble_solids = []

for c in range(cols):
    for r in range(rows):
        # Deterministic pseudo-random seed matching OpenSCAD approach
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

                # Dispatcher
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

                # Move to position (x, y, base_z)
                translated_greeble = greeble.translate((x, y, base_z))
                greeble_solids.append(translated_greeble)

# Combine all greebles and intersect with boundary bounds
if greeble_solids:
    # Batch union all greebles
    all_greebles = greeble_solids[0]
    for g in greeble_solids[1:]:
        all_greebles = all_greebles.union(g)

    # Boundary clip box (matching OpenSCAD's intersection cube)
    clip_box = cq.Workplane("XY").box(
        box_x, box_y, base_z + 25, centered=(False, False, False)
    )
    clipped_greebles = all_greebles.intersect(clip_box)

    assembly = assembly.union(clipped_greebles)

# ------------------------------------------------
# Export STEP File
# ------------------------------------------------
cq.exporters.export(assembly, "borg_surface.step")
print("Successfully exported 'borg_surface.step'")
