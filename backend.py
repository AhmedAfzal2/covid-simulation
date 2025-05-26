from flask import Flask, jsonify, request, render_template
from collections import deque
from flask_cors import CORS
import infection as inf
import graph_util as gt
import threading as th
import random as rd
import igraph as ig
import time as t

sessions = {}
def init_session(id):
    sessions[id] = {}
    
    g, countries = gt.load_graph('data/node_list.csv', 'data/edge_list_type.csv', START_NODE)
    sessions[id]['g'] = g
    sessions[id]['countries'] = countries
    sessions[id]['day'] = 0
    
    sessions[id]['quarantined'] = {}
    vax_order, vax_delay = inf.vax_route(g, countries)
    sessions[id]['vax_order'] = vax_order
    sessions[id]['vax_delay'] = vax_delay
    sessions[id]['vaccinated'] = set()
    
    sessions[id]['infection_rate'] = 0.3
    sessions[id]['incubation_period'] = 14
    sessions[id]['recovery_period'] = 20
    sessions[id]['immunity_loss_time'] = 100
    sessions[id]['mortality_rate'] = 0.001
    sessions[id]['quarantine'] = True
    sessions[id]['vaccination'] = True
    sessions[id]['start_node'] = START_NODE
    
    with buffer_lock:
        update_buffer[id] = deque()
    
def resetGraph(id):
    session = sessions[id]
    with buffer_lock:
        update_buffer[id].clear()
    
    g = session['g']
    g.vs['S'] = g.vs['population']
    g.vs['E'] = 0
    g.vs['I'] = 0
    g.vs['R'] = 0
    g.vs['D'] = 0
    g.vs['V'] = 0
    
    session['quarantined'].clear()
    session['vaccinated'].clear()
    session['day'] = 0
    session['vax_order'], session['vax_delay'] = inf.vax_route(g, session['countries'])
    
    start_node = session['start_node']
    g.vs[start_node]['S'] -= 2000
    g.vs[start_node]['E'] += 1000
    g.vs[start_node]['I'] += 1000

START_NODE = 5441

id = 0

BUFFER_SIZE = 10
update_buffer = {}
buffer_lock = th.Lock()

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

# initial graph sent to front-end
@app.route('/graph')
def getGraph():
    global id
    
    print("Session assigned:", id)
    init_session(id)
    resetGraph(id)
    
    assigned = id
    g = sessions[id]['g']
    countries = sessions[id]['countries']
    
    id += 1
    
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
            'id': sessions[assigned]['start_node'],
            'color': gt.getColor(g.vs[sessions[assigned]['start_node']]),
            'radius': gt.getRadius(2000, 0)
            },
        'sessionID': assigned
        })
    
@app.route('/settings', methods=['POST'])
def updateSettings():
    id = int(request.headers.get('sessionID'))
    if id not in sessions:
        return
    session = sessions[id]
    settings = request.form
    startNode = settings.get('start_node').lower()
    try:
        start_node_id = next(v for v in session['g'].vs if v['name'].lower() == startNode).index
    except:
        return {'node': -1}
    session['infection_rate'] = float(settings.get('infection_rate'))
    session['incubation_period'] = float(settings.get('incubation_period'))
    session['recovery_period'] = float(settings.get('recovery_period'))
    session['immunity_loss_time'] = float(settings.get('immunity_loss'))
    session['mortality_rate'] = float(settings.get('mortality_rate'))
    session['quarantine'] = bool(settings.get('quarantine'))
    session['vaccination'] = bool(settings.get('vaccination'))
    session['start_node'] = start_node_id
    print(f"New settings for session {id}.")
    resetGraph(id)
    return {'node': {
            'id': start_node_id,
            'color': gt.getColor(session['g'].vs[start_node_id]),
            'radius': gt.getRadius(2000, 0)
            }, 'countries': gt.sendCountries(session['g'], session['countries'])}

# at every step, send updates to the graph
@app.route('/update', methods=['POST'])
def getUpdate():
    id = int(request.headers.get('sessionID'))
    if id not in sessions:
        return
    # if something is available in the buffer, send the top response
    with buffer_lock:
        if update_buffer[id]:
            return jsonify(update_buffer[id].popleft())
        else:   # buffer is empty, empty steps until thread calculates next step
            print(f'Buffer for {id} empty.')
            return jsonify({'failed': True})
            
def calc_update(id):
    session = sessions[id]
    g = session['g']
    countries = session['countries']
    nodes = []
    for v in g.vs:
        if v['E'] + v['I'] > 0:
            rates = [session['infection_rate'], session['incubation_period'], session['recovery_period'], session['immunity_loss_time'], session['mortality_rate']]
            v['S'], v['E'], v['I'], v['R'], v['D'] = inf.get_next_city_step(v['S'], v['E'], v['I'], v['R'], v['D'], v['density'], v['hdi'], rates)
            if session['vaccination'] and v['country'] in session['vaccinated']:
                inf.vaccinate(v, session['day'])
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
        
    quarantined = session['quarantined']
    
    q = ''
    toSendCountries = gt.sendCountries(g, countries)
    
    if session['quarantine']:
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
            
    if session['vaccination'] and session['vax_delay'] <= 0 and len(session['vax_order']) > 0:
        for i in range(rd.randint(0, 3)):   # 0-3 countries get vaccine per day
            if len(session['vax_order']) > 0:
                session['vaccinated'].add(session['vax_order'].pop())
        
    session['vax_delay'] -= 1
    session['day'] += 1
        
    # append to buffer
    with buffer_lock:
        try:
            update_buffer[id].append({'nodes': nodes, 'edges': edges, 'countries': toSendCountries, 'quarantined': q})
        except KeyError:
            print("Key Error in calc_update:", i)

toEnd = []
toEndLock = th.Lock()
def precompute_updates():
    print('Thread started')
    while True:
        with toEndLock:
            if len(toEnd) > 0:
                with buffer_lock:
                    del update_buffer[toEnd[-1]]
                    del sessions[toEnd[-1]]
                print("Deleted data of session", toEnd[-1])
                toEnd.pop()
        t.sleep(0.1)
        
        with buffer_lock:
            keys = []
            for key in list(update_buffer.keys()):
                if len(update_buffer[key]) < BUFFER_SIZE:
                    keys.append(key)
            
        # calculate updates
        for id in keys:
            calc_update(id)

@app.route('/end', methods=['POST'])
def end():
    id = int(request.get_data(as_text=True))
    if id in sessions:
        with toEndLock:
            toEnd.append(id)
    return "ended"
         
th.Thread(target=precompute_updates, daemon=True).start()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)