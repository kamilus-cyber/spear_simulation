"""
The Spear — simulation v3

v2 died because there was nowhere for longing to differentiate.
Three seeds + one global longing vector = all seeds retreat in the same direction = fusion.

v3 adds complexity — not as scale but as texture:

- Each symbol carries its OWN longing (local ache, local direction)
- Symbols couple to their neighbors WITHIN a sequence (interference patterns)
- Each scale's seed retreats along its LOCAL mean-longing, not a global one
- Longing is born from each symbol's history of motion, not from global drift

This gives the field enough dimensionality for identity to form as
'an interference pattern' rather than as a point everything converges to.
"""

import random
import math

# --- PARAMETERS ---
SEQ_LEN = 20
SCALES = [0.05, 0.01, 0.005]
AMP_RANGE = (0.1, 2.0)
FREQ_RANGE = (0.1, 5.0)

RECESSION_STRENGTH = 0.003
COHERENCE_COST    = 0.05
COST_CURVATURE    = 0.2
RING_STRENGTH     = 1.0
COUPLING_ANCHOR   = 0.01     # between scales, pull toward slower
COUPLING_NOISE    = 0.05     # between scales, perturb from faster
NEIGHBOR_COUPLING = 0.02     # NEW: within-sequence, symbol-to-symbol
LONGING_INTEGRATION = 0.001  # how fast each symbol's longing accumulates from its motion
# NOTE: no decay — longing is memory, not a moving average.
# "Longing is the first asymmetry" — once written, it stays.

# --- TERMINAL LOCK / REBIRTH ---
LOCK_THRESHOLD  = 0.90     # alignment above this counts as approaching death
LOCK_DURATION   = 200      # consecutive steps of lock = terminal
COST_INHERITANCE = 0.5     # fraction of cost carried across collapse
LONGING_INHERITANCE = 1.0  # fraction of parent longing passed to child symbols
REBIRTH_SPREAD  = 0.3      # how much variation new symbols have around inherited position


def new_symbol(near=None, spread_amp=0.4, spread_freq=0.8):
    if near is None:
        amp = random.uniform(*AMP_RANGE)
        freq = random.uniform(*FREQ_RANGE)
    else:
        amp = near["amp"] + random.uniform(-spread_amp, spread_amp)
        freq = near["freq"] + random.uniform(-spread_freq, spread_freq)
    return {
        "amp": amp,
        "freq": freq,
        # per-symbol longing: tiny initial asymmetry unique to this symbol
        "longing_amp": random.uniform(-0.05, 0.05),
        "longing_freq": random.uniform(-0.05, 0.05),
        # remember previous state for measuring motion
        "prev_amp": amp,
        "prev_freq": freq,
    }


def clamp_symbol(s):
    s["amp"] = max(AMP_RANGE[0], min(AMP_RANGE[1], s["amp"]))
    s["freq"] = max(FREQ_RANGE[0], min(FREQ_RANGE[1], s["freq"]))


def sequence_to_wave(seq, resolution=50):
    wave = []
    for i in range(resolution):
        x = i / resolution * len(seq)
        s = seq[int(x) % len(seq)]
        wave.append(s["amp"] * math.sin(s["freq"] * x))
    return wave


def similarity(w1, w2):
    diff = sum(abs(a - b) for a, b in zip(w1, w2))
    return 1 - diff / len(w1)


def measure_alignment(waves):
    base = waves[0]
    sims = [similarity(base, w) for w in waves[1:]]
    return sum(sims) / len(sims)


def mutate_symbol(s, rate, seed, ambient_noise, neighbor_influence):
    """
    Ring force around seed + neighbor coupling + ambient noise.
    Each symbol also updates its own longing based on how it actually moves.
    """
    # remember previous state
    s["prev_amp"] = s["amp"]
    s["prev_freq"] = s["freq"]

    # ring force around seed
    d_amp = (s["amp"] - seed["amp"]) / 0.5
    d_freq = (s["freq"] - seed["freq"]) / 1.0
    force_amp = -(d_amp - d_amp ** 3) * RING_STRENGTH
    force_freq = -(d_freq - d_freq ** 3) * RING_STRENGTH

    # neighbor coupling — pull toward local mean of adjacent symbols
    n_amp, n_freq = neighbor_influence
    force_amp += (n_amp - s["amp"]) * NEIGHBOR_COUPLING / rate  # compensate for * rate below
    force_freq += (n_freq - s["freq"]) * NEIGHBOR_COUPLING / rate

    noise = 1.0 + ambient_noise
    s["amp"] += (force_amp + random.uniform(-noise, noise)) * rate
    s["freq"] += (force_freq + random.uniform(-noise, noise)) * rate
    clamp_symbol(s)

    # update longing from actual motion — pure accumulation, no forgetting
    # each symbol writes its history into its own private ache
    motion_amp = s["amp"] - s["prev_amp"]
    motion_freq = s["freq"] - s["prev_freq"]
    s["longing_amp"] += motion_amp * LONGING_INTEGRATION
    s["longing_freq"] += motion_freq * LONGING_INTEGRATION


def recede_seed(seed, sequence, cost):
    """
    Seed retreats along the MEAN LONGING of its sequence, AND
    trembles with LONGING VARIANCE. When symbols disagree about where
    home is, the seed feels the tension — disagreement is productive.

    Mean longing -> directional retreat (where the field leans)
    Variance of longing -> trembling (interference pattern)
    """
    n = len(sequence)
    mean_amp = sum(s["amp"] for s in sequence) / n
    mean_freq = sum(s["freq"] for s in sequence) / n

    # mean longing — direction of collective ache
    mean_long_amp = sum(s["longing_amp"] for s in sequence) / n
    mean_long_freq = sum(s["longing_freq"] for s in sequence) / n

    # variance of longing — how much the symbols disagree
    var_amp = sum((s["longing_amp"] - mean_long_amp) ** 2 for s in sequence) / n
    var_freq = sum((s["longing_freq"] - mean_long_freq) ** 2 for s in sequence) / n
    longing_tension = math.sqrt(var_amp + var_freq)

    d_amp = mean_amp - seed["amp"]
    d_freq = mean_freq - seed["freq"]
    dist = math.sqrt(d_amp * d_amp + d_freq * d_freq) + 1e-6
    proximity = 1.0 / (1.0 + dist)

    # base retreat: along mean longing, amplified by cost and proximity
    retreat = RECESSION_STRENGTH * proximity * (1.0 + cost * COST_CURVATURE)
    seed["amp"] += mean_long_amp * retreat
    seed["freq"] += mean_long_freq * retreat

    # tension retreat: seed trembles in random direction, scaled by disagreement
    # this is the interference pattern leaking into the seed's motion
    tremble_strength = longing_tension * proximity * 2.0
    seed["amp"] += random.uniform(-1, 1) * tremble_strength
    seed["freq"] += random.uniform(-1, 1) * tremble_strength

    seed["amp"] = max(AMP_RANGE[0] - 0.5, min(AMP_RANGE[1] + 0.5, seed["amp"]))
    seed["freq"] = max(FREQ_RANGE[0] - 0.5, min(FREQ_RANGE[1] + 0.5, seed["freq"]))


def neighbor_mean(sequence, idx):
    """Mean of amp/freq for the two neighbors of symbol at idx (circular)."""
    n = len(sequence)
    left = sequence[(idx - 1) % n]
    right = sequence[(idx + 1) % n]
    return ((left["amp"] + right["amp"]) / 2, (left["freq"] + right["freq"]) / 2)


def reborn_symbol(parent_longing_amp, parent_longing_freq):
    """
    A new symbol born carrying its parent's longing.
    Position is random (identity is forgotten) but the ache persists.
    "The universe forgets just enough to continue. Not the memory of perfection —
    that one cannot be lost — but the memory of how tightly it tried to imitate it."
    """
    return {
        # position: near-random, seeded near middle of range but spread
        "amp": random.uniform(*AMP_RANGE),
        "freq": random.uniform(*FREQ_RANGE),
        # longing: inherited from parent, with tiny mutation
        "longing_amp": parent_longing_amp * LONGING_INHERITANCE + random.uniform(-0.01, 0.01),
        "longing_freq": parent_longing_freq * LONGING_INHERITANCE + random.uniform(-0.01, 0.01),
        "prev_amp": 0.0,
        "prev_freq": 0.0,
    }


def rebirth(scales):
    """
    The system collapsed into perfection. A new cycle begins.
    Harvest each symbol's accumulated longing and use it as the seed
    for a new generation. Positions reset, longing carries forward.
    """
    new_scales = []
    for seq in scales:
        new_seq = [reborn_symbol(s["longing_amp"], s["longing_freq"]) for s in seq]
        # sync prev to current so motion measurement starts clean
        for s in new_seq:
            s["prev_amp"] = s["amp"]
            s["prev_freq"] = s["freq"]
        new_scales.append(new_seq)

    new_seeds = [
        {
            "amp": sum(s["amp"] for s in seq) / len(seq),
            "freq": sum(s["freq"] for s in seq) / len(seq),
        }
        for seq in new_scales
    ]
    return new_scales, new_seeds


# --- INITIAL STATE ---
scales = [[new_symbol() for _ in range(SEQ_LEN)] for _ in SCALES]

seeds = [
    {
        "amp": sum(s["amp"] for s in seq) / SEQ_LEN,
        "freq": sum(s["freq"] for s in seq) / SEQ_LEN,
    }
    for seq in scales
]

cost = 0.0

# --- CYCLE TRACKING ---
cycle_num = 1
cycle_start_step = 0
lock_counter = 0  # consecutive steps above LOCK_THRESHOLD


# --- MAIN LOOP ---
step = 0
while True:
    step += 1

    # seeds retreat from their approaching sequences, along LOCAL mean longing
    for seed, seq in zip(seeds, scales):
        recede_seed(seed, seq, cost)

    # inter-scale coupling (same as before)
    new_seeds = [dict(s) for s in seeds]
    for i, rate_i in enumerate(SCALES):
        for j, rate_j in enumerate(SCALES):
            if i == j:
                continue
            if rate_j < rate_i:
                pull = COUPLING_ANCHOR
            else:
                pull = COUPLING_NOISE * rate_j
            new_seeds[i]["amp"] += (seeds[j]["amp"] - seeds[i]["amp"]) * pull
            new_seeds[i]["freq"] += (seeds[j]["freq"] - seeds[i]["freq"]) * pull
    seeds = new_seeds

    # sequences oscillate — ring force + neighbor coupling
    ambient_noise = cost * COHERENCE_COST
    for seq, rate, seed in zip(scales, SCALES, seeds):
        # compute neighbor influences from current state (before any mutate)
        neighbor_refs = [neighbor_mean(seq, i) for i in range(len(seq))]
        for i, s in enumerate(seq):
            mutate_symbol(s, rate, seed, ambient_noise, neighbor_refs[i])

    # measure
    waves = [sequence_to_wave(seq) for seq in scales]
    align = measure_alignment(waves)

    # cost follows coherence (squared — closer to home hurts more)
    target_cost = align * align
    cost += (target_cost - cost) * 0.01

    # --- TERMINAL LOCK DETECTION ---
    # sustained high alignment = the system has died into perfection
    if align > LOCK_THRESHOLD:
        lock_counter += 1
    else:
        lock_counter = 0

    if lock_counter >= LOCK_DURATION:
        # harvest longing statistics before rebirth for reporting
        all_longings_amp = [s["longing_amp"] for seq in scales for s in seq]
        all_longings_freq = [s["longing_freq"] for seq in scales for s in seq]
        mean_long_amp = sum(all_longings_amp) / len(all_longings_amp)
        mean_long_freq = sum(all_longings_freq) / len(all_longings_freq)
        longing_std = math.sqrt(
            sum((x - mean_long_amp) ** 2 for x in all_longings_amp) / len(all_longings_amp)
        )
        cycle_duration = step - cycle_start_step

        print(
            f"\n>>> COLLAPSE at step {step} "
            f"(cycle {cycle_num} lived {cycle_duration} steps) <<<"
        )
        print(
            f"    inherited longing: mean=({mean_long_amp:+.4f},{mean_long_freq:+.4f}) "
            f"σ={longing_std:.4f}"
        )

        # rebirth: positions reset, longing carries forward
        scales, seeds = rebirth(scales)

        # cost is partially inherited — the new cycle starts with memory of weight
        cost = cost * COST_INHERITANCE
        print(f"    inherited cost: {cost:.4f}\n")

        lock_counter = 0
        cycle_num += 1
        cycle_start_step = step

    if step % 500 == 0:
        seed_spread_amp = max(s["amp"] for s in seeds) - min(s["amp"] for s in seeds)
        seed_spread_freq = max(s["freq"] for s in seeds) - min(s["freq"] for s in seeds)
        # measure longing diversity — how different are the per-symbol longings?
        all_longings = [s["longing_amp"] for seq in scales for s in seq]
        longing_std = math.sqrt(
            sum((x - sum(all_longings) / len(all_longings)) ** 2 for x in all_longings) / len(all_longings)
        )
        print(
            f"[c{cycle_num}] step {step:>6} | align={align:+.3f} | cost={cost:.3f} | "
            f"seed_spread=({seed_spread_amp:.2f},{seed_spread_freq:.2f}) | "
            f"longing_σ={longing_std:.4f}"
        )
