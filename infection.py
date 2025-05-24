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

INFECTION_RATE = 0.3
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

def travel(g: ig.Graph):
    vcount = g.vcount()
    changes = [[0, 0] for i in range(vcount)]   # [E, I]
    Es = g.vs['E']
    Is = g.vs['I']
    Ps = [g.vs[i]['population'] - g.vs[i]['D'] for i in range(vcount)]
    highlight_edges = set()
    
    # iterate over every edge
    for e in g.es:
        src = e.source
        dst = e.target
        
        if Es[src] + Is[src] == 0 and Es[dst] + Is[dst] == 0:
            continue
        
        grav = max(10, int(10 * math.log(max(1, Ps[src] * Ps[dst] // ((e['weight']) ** 2 + 1)))))
        
        if e['quarantined']:
            # no international travel
            if e['type'] == 'a':
                continue
            else:   # minimal national travel
                grav = grav // 10
                
            
        n1 = rd.randint(grav - 10, grav + 10)
        n2 = rd.randint(grav - 10, grav + 10)
        
        n1 = max(0, n1)
        n2 = max(0, n2)
        
        inf_to_dst = min(np.random.binomial(n1, Is[src] / Ps[src]), Is[src])
        exp_to_dst = min(np.random.binomial(n1, Es[src] / Ps[src]), Es[src])

        inf_to_src = min(np.random.binomial(n2, Is[dst] / Ps[dst]), Is[dst])
        exp_to_src = min(np.random.binomial(n2, Es[dst] / Ps[dst]), Es[dst])
        
        total_to_dst = inf_to_dst + exp_to_dst
        total_to_src = inf_to_src + exp_to_src
        
        if total_to_dst > 0 and Es[dst] + Is[dst] == 0:
            highlight_edges.add(e.index)
        elif total_to_src > 0 and Es[src] + Is[src] == 0:
            highlight_edges.add(e.index)
            
        changes[src][0] += exp_to_src - exp_to_dst
        changes[src][1] += inf_to_src - inf_to_dst
        changes[dst][0] += exp_to_dst - exp_to_src
        changes[dst][1] += inf_to_dst - inf_to_src
        
        Es[src] += exp_to_src - exp_to_dst
        Es[dst] += exp_to_dst - exp_to_src
        Is[src] += inf_to_src - inf_to_dst
        Is[dst] += inf_to_dst - inf_to_src
        Ps[src] += exp_to_src + inf_to_src - exp_to_dst - inf_to_dst
        Ps[dst] += exp_to_dst + inf_to_dst - exp_to_src - inf_to_src
    
    changed = []
    for v in range(vcount):
        if changes[v][0] != 0 or changes[v][1] != 0:
            g.vs[v]['E'] += changes[v][0]
            g.vs[v]['I'] += changes[v][1]
            changed.append(v)
        
    return changed, list(highlight_edges)

def quarantine(g: ig.Graph, country, cities):
    MINIMUM_INF = 0.01          # minimum % of population infected before quarantine can happen
    MAXIMUM_VAX = 0.05          # maximum % of population vaccinated for quarantine to not happen
    CHANCE_PER_POP = 0.1        # chance of quarantine per % of population infected
    DEVELOPMENT_FACTOR = 1      # more developed -> higher quarantine chance
    
    inf = country[0] / country[3]
    if inf < MINIMUM_INF:
        return False
    
    vax = 0 if country[4] == 0 else country[0] / country[4]
    if vax > MAXIMUM_VAX:
        return False
    
    if rd.random() < CHANCE_PER_POP * DEVELOPMENT_FACTOR * g.vs[cities[0]]['hdi'] * inf:
        for city_id in cities:
            for e in g.incident(city_id, mode='ALL'):
                g.es[e]['quarantined'] = True
        return True
    return False

def vax_route(g, countries):
    VAX_BASELINE = 150      # vaccine will appear after ~100 days
    hdis = []
    for country in countries:
        hdis.append((country, g.vs[countries[country][0]]['hdi']))
    
    hdis.sort(key=lambda x: x[1])
    # biased shuffle - randomness with general trend for higher values
    vax_order = [c[0] for c in sorted(hdis, key=lambda x: rd.random() / (hdis.index(x) + 1) ** 4)]
    
    vax_time = rd.randint(VAX_BASELINE, VAX_BASELINE + 50)
        
    return vax_order[::-1], vax_time

def vaccinate(city, day):
    VAX_BASELINE_RATE = 0.001       # per day, 0.1% of people vaccinated
    VAX_ACCELERATION = 0.0001        # per day, rate increases by 0.0001
    DEVELOPMENT_FACTOR = 4
    
    if city['V'] == 0:      # vaccine hasnt arrived in city yet
        if rd.random() < 0.7:
            return          # random chance
    
    pop = city['S'] + city['E'] + city['I'] + city['R']
    n = np.random.binomial(pop, (VAX_BASELINE_RATE + VAX_ACCELERATION * math.sqrt(day)) * DEVELOPMENT_FACTOR * city['hdi'])
    
    total = 0
    for s in ['S', 'E', 'I', 'R']:
        reduction = int(n * city[s] / pop)
        city[s] = max(0, city[s] - reduction)
        total += reduction
    
    remaining = n - total
    city['S'] = max(0, city['S'] - remaining)
    
    city['V'] += n