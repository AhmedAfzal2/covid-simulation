import igraph as ig
import pandas as pd
import math
import csv

def latlon_to_xy(lat, lon):
    x = math.radians(lon)
    y = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y

def load_graph(node_file, edge_file, start):
    g = ig.Graph()
    countries: dict[str, list[int]] = {}
    
    with open(node_file) as node_list:
        reader = csv.reader(node_list)
        for row in reader:
            v = g.add_vertex(name=row[1], country=row[2], lat=float(row[3]), lon=float(row[4]), population=int(row[5]), density=float(row[6]), hdi=float(row[7]), S = int(row[5]))
            if v['country'] in countries:
                countries[v['country']].append(v.index)
            else:
                countries[v['country']] = [v.index]
    
    g.vs['E'] = 0
    g.vs['I'] = 0
    g.vs['R'] = 0
    g.vs['D'] = 0
    g.vs['V'] = 0 

    edge_list = pd.read_csv(edge_file, header=None)
    edge_list.columns = ['src', 'dest', 'weight', 'type', 'in_mst']
    edges = list(zip(edge_list['src'], edge_list['dest']))
    
    g.add_edges(edges)
    g.es['weight'] = edge_list['weight'].tolist()
    g.es['type'] = edge_list['type'].tolist()
    g.es['in_mst'] = edge_list['in_mst'].tolist()
    g.es['quarantined'] = False
    
    g.vs[start]['S'] -= 2000
    g.vs[start]['E'] += 1000
    g.vs[start]['I'] += 1000
    
    return g, countries
    
def sendCountries(g, countries):
    toSend = {}
    totalInf = 0
    totalRecov = 0
    totalDead = 0
    totalPop = 0
    totalVax = 0
    totalSus = 0
    totalExp = 0
    for country, cities in countries.items():
        inf = 0
        recov = 0
        dead = 0
        pop = 0
        vax = 0
        sus = 0
        exp = 0
        for city_id in cities:
            city = g.vs[city_id]
            inf += city['I']
            recov += city['R']
            dead += city['D']
            vax += city['V']
            pop += city['population']
            sus += city['S']
            exp += city['E']
        totalInf += inf
        totalRecov += recov
        totalDead += dead
        totalPop += pop
        totalVax += vax
        totalSus += sus
        totalExp += exp
        toSend[country] = [inf, recov, dead, pop, vax]
    toSend['World'] = [totalInf, totalRecov, totalDead, totalPop, totalVax, totalSus, totalExp]
    return toSend

def easeInSine(x):
    return 1 - math.cos((x * math.pi) / 2);


# node color to show on front-end
def getColor(v):
    # cities with more dead people appear darker red
    darken = (1 - v['D'] / v['population']) ** 2
    # vaccination is blue
    blue = v['V'] / v['population']
    # the more infected, the more opaque
    transparent = (v['E'] + v['I']) / v['population']
    
    red = 255
    if blue != 0:
        red -= 150 * blue
    
    return [int(red * darken), easeInSine(transparent), int(255 * blue * darken)]

# linear interpolation to convert from population to marker radius
def getRadius(inf_population, vax_pop):
    if inf_population == 0 and vax_pop == 0:
        return 0
    MAX_POPULATION = 3000000
    MIN_RADIUS = 2
    MAX_RADIUS = 10
    p = max(inf_population, vax_pop)
    p = min(p, MAX_POPULATION)
    return MIN_RADIUS + (p / MAX_POPULATION) * (MAX_RADIUS - MIN_RADIUS)