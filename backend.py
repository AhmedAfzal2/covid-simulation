from flask import Flask, jsonify
from collections import deque
from flask_cors import CORS
import infection as inf
import graph_util as gt
import threading as th
import random as rd
import igraph as ig
import time as t

def resetGraph():
    global day, vax_delay, vax_order
    with buffer_lock:
        update_buffer.clear()
    
    g.vs['S'] = g.vs['population']
    g.vs['E'] = 0
    g.vs['I'] = 0
    g.vs['R'] = 0
    g.vs['D'] = 0
    g.vs['V'] = 0
    
    quarantined.clear()
    vaccinated.clear()
    day = 0
    vax_order, vax_delay = inf.vax_route(g, countries)
    
    g.vs[START_NODE]['S'] -= 2000
    g.vs[START_NODE]['E'] += 1000
    g.vs[START_NODE]['I'] += 1000

START_NODE = 5441
g, countries = gt.load_graph('data/node_list.csv', 'data/edge_list_type.csv', START_NODE)
day = 0
quarantined = {}
vax_order, vax_delay = inf.vax_route(g, countries)
vaccinated = set()
update_buffer = deque()
BUFFER_SIZE = 10
buffer_lock = th.Lock()
app = Flask(__name__)
CORS(app)

# initial graph sent to front-end
@app.route('/graph')
def getGraph():
    resetGraph()
    nodes = []
    for v in g.vs:
        x, y = gt.latlon_to_xy(v['lat'], v['lon'])
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
    
    return jsonify({
        'nodes': nodes,
        'edges': edges,
        'countries': gt.sendCountries(g, countries),
        'startNode': {
            'id': START_NODE,
            'color': gt.getColor(g.vs[START_NODE]),
            'radius': gt.getRadius(2000, 0)
            }
        })

# at every step, send updates to the graph
@app.route('/update')
def getUpdate():
    # if something is available in the buffer, send the top response
    with buffer_lock:
        if update_buffer:
            return jsonify(update_buffer.popleft())
        else:   # buffer is empty, empty steps until thread calculates next step
            print('no')
            return jsonify({'nodes': [], 'edges': [], 'countries': gt.sendCountries(g, countries), 'quarantined': ''})
            
def precompute_updates():
    global vax_delay, day
    while True:
        t.sleep(0.1)
        with buffer_lock:
            # pause if buffer is full
            if len(update_buffer) >= BUFFER_SIZE:
                continue
        
        # calculate update
        nodes = []
        for v in g.vs:
            if v['E'] + v['I'] > 0:
                v['S'], v['E'], v['I'], v['R'], v['D'] = inf.get_next_city_step(v['S'], v['E'], v['I'], v['R'], v['D'], v['density'], v['hdi'])
                if v['country'] in vaccinated:
                    inf.vaccinate(v, day)
                nodes.append({
                    'id': v.index,
                    'color': gt.getColor(v),
                    'radius': gt.getRadius(v['E'] + v['I'], v['V'])
                })

        try:
            changed, edges = inf.travel(g)
        except Exception as e:
            print(e)
            raise Exception("e")
        
        for i in changed:
            v = g.vs[i]
            nodes.append({
                'id': v.index,
                'color': gt.getColor(v),
                'radius': gt.getRadius(v['E'] + v['I'], v['V'])
            })
        
        q = ''
        toSendCountries = gt.sendCountries(g, countries)
        for country, info in toSendCountries.items():
            if country == 'World' or country in quarantined:
                continue
            if inf.quarantine(g, info, countries[country]):
                q = country
                quarantined[country] = rd.randint(10, 40)   # quarantine duration
                break   # only one country can quarantine per step
            
        for country in list(quarantined.keys()):
            quarantined[country] -= 1
            if quarantined[country] < 0:
                for city_id in countries[country]:
                    for e in g.incident(city_id, mode='ALL'):
                        g.es[e]['quarantined'] = False
                del quarantined[country]
                q = country
                
        if vax_delay <= 0 and len(vax_order) > 0:
            for i in range(rd.randint(0, 3)):   # 0-3 countries get vaccine per day
                if len(vax_order) > 0:
                    vaccinated.add(vax_order.pop())
            
        vax_delay -= 1
        day += 1
            
        # append to buffer
        with buffer_lock:
            update_buffer.append({'nodes': nodes, 'edges': edges, 'countries': toSendCountries, 'quarantined': q})
            

if __name__ == '__main__':
    th.Thread(target=precompute_updates, daemon=True).start()
    app.run(debug=True)