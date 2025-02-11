# Trip cost optimising as linear programming problem

## Linear programming (LP)

In Linear Programming (LP), we define a function that we need to optimise,

$$
f(x_1, ..., x_i) = c_1 * x_1 + ... + c_i * x_i
$$

And a set of constraints we want the solution to meet These constraints are expressed as
inequalities.

$$
a_11 * x_1 + ... + a_1i * x_i >= b_1
a_21 * x_2 + ... + a_2i * x_i >= b_2
$$

We want to find a set of values $x_1, ..., x_i$ such that all inequalities hold, and the
value of $f()$ is minimal.

---

## Applying LP to optimise trip cost

**Goal**: Minimise total cost of the trip.

**Constraints**:

- Starts on or after 2025-02-21, 21:00
- Ends after 2025-02-23, 23:00

**Variables**:

- transport
    - outward
    - inward
    - internal (changes based on location of accommodation, total days of trip)
- accommodation (may include one meal)
    - location
    - start date
    - end date
- food (fixed cost per meal, 3 meals per day at specific times, no cost of meal if meal
  is taken while on transport)

---

### Defining a Function for the Problem

Transport = Outward +
            Inward +
            Accommodation-Airport +
            Airport-Accommodation +
            Accommodation-Event +
            Event-Accommodation

Accommodation = Number of Nights * Accommodation

Food = Dinner + Lunch + (Breakfast if not provided by Accommodation)

Total =  Transport + Accommodation + Food
