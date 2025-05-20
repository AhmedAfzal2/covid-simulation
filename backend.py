from flask import Flask, jsonify
from flask_cors import CORS
import infection as inf
import igraph as ig
import pandas as pd
import time as t
import math
import csv

def latlon_to_xy(lat, lon):
    R = 6378137     # earth radius
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y

def load_graph(node_file, edge_file):
    g = ig.Graph()
    countries: dict[str, list[ig.Vertex]] = {}
    
    with open(node_file) as node_list:
        reader = csv.reader(node_list)
        for row in reader:
            v = g.add_vertex(name=row[1], country=row[2], lat=float(row[3]), lon=float(row[4]), population=int(row[5]), density=float(row[6]), hdi=float(row[7]), S = int(row[5]))
            if v['country'] in countries:
                countries[v['country']].append(v)
            else:
                countries[v['country']] = [v]
    
    g.vs['E'] = 0
    g.vs['I'] = 0
    g.vs['R'] = 0
    g.vs['D'] = 0

    edge_list = pd.read_csv(edge_file, header=None)
    edge_list.columns = ['src', 'dest', 'weight', 'type', 'in_mst']
    edges = list(zip(edge_list['src'], edge_list['dest']))
    
    g.add_edges(edges)
    g.es['weight'] = edge_list['weight'].tolist()
    g.es['type'] = edge_list['type'].tolist()
    g.es['in_mst'] = edge_list['in_mst'].tolist()
    
    g.vs[3901]['S'] -= 10000
    g.vs[3901]['E'] += 5000
    g.vs[3901]['I'] += 5000
    
    return g, countries

def resetGraph():
    g.vs['S'] = g.vs['population']
    g.vs['E'] = 0
    g.vs['I'] = 0
    g.vs['R'] = 0
    g.vs['D'] = 0
    
    g.vs[3901]['S'] -= 10000
    g.vs[3901]['E'] += 5000
    g.vs[3901]['I'] += 5000
    
def sendCountries(countries):
    toSend = {}
    totalInf = 0
    totalRecov = 0
    totalDead = 0
    totalPop = 0
    for country, cities in countries.items():
        inf = 0
        recov = 0
        dead = 0
        pop = 0
        for city in cities:
            inf += city['I']
            recov += city['R']
            dead += city['D']
            pop += city['population']
        totalInf += inf
        totalRecov += recov
        totalDead += dead
        totalPop += pop
        toSend[country] = [inf, recov, dead, pop]
    toSend['World'] = [totalInf, totalRecov, totalDead, totalPop]
    return toSend

# node color to show on front-end
def getColor(v):
    # cities with more dead people appear darker red
    darken = 1 - v['D'] / v['population']
    # the more infected, the more opaque
    transparent = (v['E'] + v['I']) / v['population']
    return [int(255 * darken), transparent]

# linear interpolation to convert from population to marker radius
def getRadius(population):
    MAX_POPULATION = 3000000
    MIN_RADIUS = 4
    MAX_RADIUS = 10
    p = min(population, MAX_POPULATION)
    return MIN_RADIUS + (p / MAX_POPULATION) * (MAX_RADIUS - MIN_RADIUS)

g, countries = load_graph('data/node_list.csv', 'data/edge_list_type.csv')
app = Flask(__name__)
CORS(app)

# initial graph sent to front-end
@app.route('/graph')
def getGraph():
    resetGraph()
    nodes = []
    for v in g.vs:
        x, y = latlon_to_xy(v['lat'], v['lon'])
        nodes.append({
            'id': v.index,
            'x': x,
            'y': y,
            'lat': v['lat'],
            'lon': v['lon'],
            'size': 3,
            'fixed': True
        })
    
    # takes edges in a spanning tree + all airport edges
    edges = []
    for e in g.es:
        if e['in_mst'] or e['type'] == 'a':
            edges.append({'id': e.index, 'from': e.source, 'to': e.target})
    
    return jsonify({'nodes': nodes, 'edges': edges, 'countries': sendCountries(countries)})

# at every step, send updates to the graph
# nodes = [3901]
# visited = set()
# visited.add(3901)
@app.route('/update')
def getUpdate():
    # global nodes, visited
    # toAdd = []
    # ret = []
    nodes = []

    s = t.time()
    for v in g.vs:
        if v['E'] + v['I'] > 0:
            v['S'], v['E'], v['I'], v['R'], v['D'] = inf.get_next_city_step(v['S'], v['E'], v['I'], v['R'], v['D'], v['density'], v['hdi'])
            nodes.append({
                'id': v.index,
                'color': getColor(v),
                'radius': getRadius(v['E'] + v['I'])
            })
    e = t.time()
    print(e - s)
    
    changed, edges = inf.travel(g)
    s = t.time()
    print(s - e)
    for i in changed:
        v = g.vs[i]
        nodes.append({
            'id': v.index,
            'color': getColor(v),
            'radius': getRadius(v['E'] + v['I'])
        })
    # while len(nodes) > 0:
    #     a = nodes.pop()
    #     for ei in g.incident(a):
    #         edge = g.es[ei]
    #         neighbor = edge.source if edge.target == a else edge.target
    #         if neighbor not in visited:
    #             visited.add(neighbor)
    #             toAdd.append(neighbor)
    #             ret.append({
    #                 'id': neighbor,
    #                 'color': '#ff0000'
    #             })

    # for i in toAdd:
    #     nodes.append(i)


    return jsonify({'nodes': nodes, 'edges': edges, 'countries': sendCountries(countries)})
            

if __name__ == '__main__':
    app.run(debug=True)