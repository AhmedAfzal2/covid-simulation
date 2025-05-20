import igraph as ig
import random as rd
import numpy as np
import math

# SEIRD model used
# S - Susceptible
# E - Exposed
# I - Infected
# R - Recovered
# D - Dead

# infct - infection rate
# incub - 1 / incubation period
# recov - 1 / recovery time
# immloss - 1 / time to lose immunity
# death - death rate

# this creates a differential equation based on the SEIRD model
def diff_eq(initial, t, N, infct, incub, recov, immloss, death):
    S, E, I, R, D = initial
    dSdt = immloss * R - infct * S * I / N
    dEdt = infct * S * I / N - incub * E
    dIdt = incub * E - recov * I - death * I
    dRdt = recov * I - immloss * R
    dDdt = death * I
    
    return np.array([dSdt, dEdt, dIdt, dRdt, dDdt])

INFECTION_RATE = 0.4
DENSITY_FACTOR = 0.5
BASELINE_DENSITY = 100
INCUBATION_PERIOD = 14
RECOVERY_PERIOD = 20
IMMUNITY_LOSS_TIME = 100
DEVELOPMENT_FACTOR = 1 / 3
MORTALITY = 0.001

# returns the number of S, E, I, R, D people in the next step
# population density and human development are used to calculate parameters of SEIRD model
def get_next_city_step(S, E, I, R, D, density, development):
    N = S + E + I + R
    # infection rate increases logarithmically with density
    infct = INFECTION_RATE * (1 + 0.5 * math.log(density / BASELINE_DENSITY + 0.5))
    incub = 1 / INCUBATION_PERIOD
    # recovery period is shorter for more developed countries
    recov = 1 / (RECOVERY_PERIOD * (1 - development * DEVELOPMENT_FACTOR))
    immloss = 1 / (IMMUNITY_LOSS_TIME)
    # death rate reduces quadratically with development
    death = MORTALITY * (1 - development * development * DEVELOPMENT_FACTOR)
    
    output = rk4_step(diff_eq, np.array([S, E, I, R, D]), 0, 1, N, infct, incub, recov, immloss, death)
    
    return np.round(output).astype(int).tolist()

# use runge-kutta to approximate a solution of the differential equation
def rk4_step(f, y, t, dt, *args):
    k1 = f(y, t, *args)
    k2 = f(y + dt * k1 / 2, t + dt / 2, *args)
    k3 = f(y + dt * k2 / 2, t + dt / 2, *args)
    k4 = f(y + dt * k3, t + dt, *args)
    return y + dt * (k1 + 2*k2 + 2*k3 + k4) / 6

def travel(g: ig.Graph, ajl):
    # 2d array to 'buffer' changes in populations of each city
    # changes[n][0] represents change in exposed for nth city, 1 is infected
    vcount = g.vcount()
    changes = [[0 for i in range(2)] for i in range(vcount)]
    Es = g.vs['E']
    Is = g.vs['I']
    pops = g.vs['population']
    Ds = g.vs['D']
    highlight_edges = set()
    
    # travel is only relevant for infected or exposed people
    # we can ignore others and assume they cancel out across populations
    active_cities = [i for i in range(vcount) if Es[i] > 0 or Is[i] > 0]

    for vi in active_cities:
        pop = max(pops[vi] - Ds[vi], Es[vi] + Is[vi] + g.vs[vi]['S'] + g.vs[vi]['R'])   # exclude dead people
        if pop == 0:
            continue

        edges = ajl[vi]
        for e in edges:
            target_i = e[0] if e[1] == vi else e[1]
            
            target_pop = pops[target_i] - Ds[target_i]
            if e[3] == 'c':
                # determining number of people travelling with a 'gravity' approach
                n = max(1, min(pop * target_pop // ((e[2] * 1000) ** 2 + 2), pop // 100))
                
            else:
                # 1 flight per 100000 people assumed
                # each flight contains between 50 and 400 people randomly
                n = max(1, min(rd.randint(1, pop // 100000 + 1) * rd.randint(50, 400), pop // 100))
            exposed_travelers = np.random.binomial(n, min(Es[vi] / pop, 1))     # incorporates randomness
            infected_travelers = np.random.binomial(n, min(Is[vi] / pop, 1))
            
            # highlight when the infection spreads across countries
            if exposed_travelers + infected_travelers > 0 and e[3] == 'a' and Es[target_i] + Is[target_i] == 0:
                highlight_edges.add(e[4])
        
            changes[vi][0] -= exposed_travelers
            changes[vi][1] -= infected_travelers
            changes[target_i][0] += exposed_travelers
            changes[target_i][1] += infected_travelers
    
    changed = []
    for i in range(len(changes)):
        if changes[i][0] != 0 and changes[i][1] != 0:
            g.vs[i]['E'] += changes[i][0]
            g.vs[i]['I'] += changes[i][1]
            if g.vs[i]['E'] < 0:
                g.vs[i]['E'] = 0
            if g.vs[i]['I'] < 0:
                g.vs[i]['I'] = 0
            changed.append(i)
            
    return changed, list(highlight_edges)
