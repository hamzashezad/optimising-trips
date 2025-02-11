import math
from datetime import date, datetime, time

import pulp

from data import (
    accommodation_options,
    inward_transport_options,
    outward_transport_options,
)

# ----------------------------
# 1. Define Sample Data
# ----------------------------

# Date format and required time parameters
min_out_dep = datetime.fromisoformat("2025-02-21T21:00:00+05:00")
min_in_dep = datetime.fromisoformat("2025-02-23T23:00:00+05:00")

required_date = date(2025, 2, 23)
required_start_time = time(12, 0)  # 12:00
required_end_time = time(23, 0)  # 23:00

# Filter outward options by departure time constraint
out_options = [
    opt
    for opt in outward_transport_options
    if opt.dep >= min_out_dep
    and (opt.type != "train" or (time(11, 0) <= opt.arr.time() <= time(20, 0)))
]

# Filter inward options by departure time constraint
in_options = [
    opt
    for opt in inward_transport_options
    if opt.dep >= min_in_dep
    and (opt.type != "train" or (time(7, 0) <= opt.dep.time() <= time(15, 0)))
]

# Accommodation options (each option: id, cost, check-in, check-out, breakfast indicator, internal transport cost)
acc_options = accommodation_options

# Filter accommodation options so that check-in is on or before 18:00 and checkout is on or after 23:00 on 2025-02-23.
# acc_options = [
#     acc
#     for acc in acc_options
#     if acc["checkin"] <= req_checkin and acc["checkout"] >= req_checkout
# ]

# Build dictionaries and id lists for easy lookup.
out_dict = {opt.id: opt for opt in out_options}
in_dict = {opt.id: opt for opt in in_options}
acc_dict = {acc.id: acc for acc in acc_options}

out_ids: list[str] = [opt.id for opt in out_options]
in_ids: list[str] = [opt.id for opt in in_options]
acc_ids: list[str] = [acc.id for acc in acc_options]

# ---------------------
# Food Costs (per meal)
# ---------------------
f_bf = 3000  # breakfast cost
f_lunch = 3000  # lunch cost
f_dinner = 4000  # dinner cost

# ---------------------------------------------------
# 2. Define Helper Functions
# ---------------------------------------------------
def meets_required_window(out_arr: datetime, in_dep: datetime):
    """
    Returns True if the flight combination ensures that the traveler is in Karachi during
    the required window: on required_date between required_start_time and required_end_time.

    Conditions:
      - If the outward flight arrives on the required_date, it must arrive no later than required_start_time.
        If it arrives before the required_date, the condition is automatically met.
      - If the inward flight departs on the required_date, it must depart no earlier than required_end_time.
        If it departs after the required_date, the condition is met.
    """
    # Check arrival condition
    if out_arr.date() < required_date:
        arrival_ok = True
    elif out_arr.date() == required_date:
        arrival_ok = out_arr.time() <= required_start_time
    else:
        arrival_ok = False

    # Check departure condition
    if in_dep.date() > required_date:
        departure_ok = True
    elif in_dep.date() == required_date:
        departure_ok = in_dep.time() >= required_end_time
    else:
        departure_ok = False

    return arrival_ok and departure_ok


# ---------------------------------------------------
# 3. Generate Feasible Combinations and Compute Nights
# ---------------------------------------------------

w_keys: list[tuple[str, str, str]] = []  # keys for combination decision variables
D = {}

for i in out_ids:
    for j in in_ids:
        # Ensure the inward flight departs after or at the outward flight arrival.
        if in_dict[j].dep >= out_dict[i].arr:
            # Check that the flight combination meets the required presence window in Karachi.
            if not meets_required_window(
                out_dict[i].arr,
                in_dict[j].dep,
            ):
                continue

            delta_days = (in_dict[j].dep - out_dict[i].arr).total_seconds() / (3600 * 24)
            D_ij = math.ceil(delta_days)
            D[(i, j)] = D_ij
            for k in acc_ids:
                w_keys.append((i, j, k))

# ---------------------------------------------------
# 4. Build the MILP Model Using PuLP
# ---------------------------------------------------

model = pulp.LpProblem("TravelCostOptimization", pulp.LpMinimize)

# Decision variables:
# x[i]: binary variable for choosing outward flight option i.
x = pulp.LpVariable.dicts("x", out_ids, cat="Binary")

# y[j]: binary variable for choosing inward flight option j.
y = pulp.LpVariable.dicts("y", in_ids, cat="Binary")

# z[k]: binary variable for choosing accommodation option k.
z = pulp.LpVariable.dicts("z", acc_ids, cat="Binary")

# w[(i,j,k)]: binary variable for the combination of outward flight i, inward flight j, and accommodation k.
w = pulp.LpVariable.dicts("w", w_keys, cat="Binary")

# ---------------------
# 4a. Selection Constraints
# ---------------------
model += pulp.lpSum([x[i] for i in out_ids]) == 1, "SelectOneOutward"
model += pulp.lpSum([y[j] for j in in_ids]) == 1, "SelectOneInward"
model += pulp.lpSum([z[k] for k in acc_ids]) == 1, "SelectOneAccommodation"
model += pulp.lpSum([w[key] for key in w_keys]) == 1, "SelectOneCombination"

# ---------------------
# 4b. Linking Constraints
# ---------------------
for i, j, k in w_keys:
    model += w[(i, j, k)] <= x[i], f"Link_w_x_{i}_{j}_{k}"
    model += w[(i, j, k)] <= y[j], f"Link_w_y_{i}_{j}_{k}"
    model += w[(i, j, k)] <= z[k], f"Link_w_z_{i}_{j}_{k}"
    model += w[(i, j, k)] >= x[i] + y[j] + z[k] - 2, f"Link_w_xyz_{i}_{j}_{k}"

# ---------------------------------------------------
# 5. Define the Objective Function
# ---------------------------------------------------

# Transportation cost includes:
#   - Outward travel cost
#   - Inward travel cost
transport_cost = pulp.lpSum([out_dict[i].cost * x[i] for i in out_ids]) + pulp.lpSum(
    [in_dict[j].cost * y[j] for j in in_ids]
)

# Accommodation cost multiplied by the number of nights:
accommodation_cost = pulp.lpSum(
    [acc_dict[k].cost_per_night * D[(i, j)] * w[(i, j, k)] for (i, j, k) in w_keys]
)


# Food cost:
# For each combination (i,j,k), the daily food cost is:
#   (lunch + dinner + breakfast cost if not included)
# and then multiplied by the number of days D[(i,j)].
food_cost = pulp.lpSum(
    [
        (f_lunch + f_dinner + f_bf * (1 - acc_dict[k].breakfast_included))
        * D[(i, j)]
        * w[(i, j, k)]
        for (i, j, k) in w_keys
    ]
)

# Internal transport cost (to/from the airport) that depends on the accommodation location.
internal_transport_cost = pulp.lpSum(
    [acc_dict[k].internal_cost * w[(i, j, k)] for (i, j, k) in w_keys]
)


# Total objective: minimize total cost.
model += (
    transport_cost + accommodation_cost + food_cost + internal_transport_cost,
    "TotalCost",
)

def print_solution_costs():
    if model.status != pulp.LpStatusOptimal:
        print(f"Model status: {model.status}")
        return
        
    print("\n=== Selected Variables ===")
    
    # Print selected outward flight
    print("\nSelected Outward Flight:")
    for i in out_ids:
        if x[i].value() > 0.9:
            print(f"Flight {i}: {out_dict[i]}")
            
    # Print selected inward flight
    print("\nSelected Inward Flight:")
    for j in in_ids:
        if y[j].value() > 0.9:
            print(f"Flight {j}: {in_dict[j]}")
            
    # Print selected accommodation
    print("\nSelected Accommodation:")
    for k in acc_ids:
        if z[k].value() > 0.9:
            print(f"Accommodation {k}: {acc_dict[k]}")
            
    # Print selected combinations
    print("\nSelected Combinations (w variables):")
    for (i,j,k) in w_keys:
        if w[(i,j,k)].value() > 0.9:
            print(f"Combination: out={i}, in={j}, acc={k}")
            print(f"Number of nights (D[(i,j)]): {D[(i,j)]}")
            print(f"Accommodation cost per night: {acc_dict[k].cost_per_night}")
            
    # Print detailed costs
    print("\n=== Detailed Costs ===")
    trans_cost = sum(out_dict[i].cost * x[i].value() for i in out_ids) + \
                sum(in_dict[j].cost * y[j].value() for j in in_ids)
    
    acc_cost = sum(acc_dict[k].cost_per_night * D[(i,j)] * w[(i,j,k)].value() 
                  for (i,j,k) in w_keys)
    
    food_c = sum((f_lunch + f_dinner + f_bf * (1 - acc_dict[k].breakfast_included))
                * D[(i,j)] * w[(i,j,k)].value() for (i,j,k) in w_keys)
    
    int_trans_c = sum(acc_dict[k].internal_cost * w[(i,j,k)].value() 
                     for (i,j,k) in w_keys)
    
    print(f"Transport cost: {trans_cost}")
    print(f"Accommodation cost: {acc_cost}")
    print(f"Food cost: {food_c}")
    print(f"Internal transport cost: {int_trans_c}")
    print(f"Total cost: {pulp.value(model.objective)}")

# ---------------------------------------------------
# 6. Solve the Model
# ---------------------------------------------------
"""
print("Solving the model...")
model.solve()
print("Status:", pulp.LpStatus[model.status])

# ---------------------------------------------------
# 7. Output the Selected Options
# ---------------------------------------------------
print("\nSelected Outward Flight Option:")
for i in out_ids:
    if pulp.value(x[i]) == 1:
        opt = out_dict[i]
        print(
            f"  {i}:  Cost {opt['cost']},  Departure {opt['dep']},  Arrival {opt['arr']}"
        )

print("\nSelected Inward Flight Option:")
for j in in_ids:
    if pulp.value(y[j]) == 1:
        opt = in_dict[j]
        print(f"  {j}:  Cost {opt['cost']},  Departure {opt['dep']}")

print("\nSelected Accommodation Option:")
for k in acc_ids:
    if pulp.value(z[k]) == 1:
        acc = acc_dict[k]
        if k == "acc_none":
            print("  No accommodation selected (same-day travel)")
        else:
            print(
                f"  {k}:  Cost per night {acc['cost_per_night']}, Checkin {acc['checkin']}, "
                f"  Checkout {acc['checkout']},  Breakfast Included: {acc['breakfast_included']}, "
                f"  Internal Transport Cost: {acc['internal_cost']}"
            )

print("\nSelected Combination (Outward, Inward, Accommodation):")
for i, j, k in w_keys:
    if pulp.value(w[(i, j, k)]) == 1:
        nights = Nights[(i, j)]
        print(
            f"Combination: (Outward: {i}, Inward: {j}, Accommodation: {k}), Nights: {nights}"
        )

print("\nTotal Optimized Cost:", pulp.value(model.objective))
"""
