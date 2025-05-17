from flask import Flask, jsonify
from flask_cors import CORS
import igraph as ig
import pandas as pd
import math
import csv

def latlon_to_xy(lat, lon):
    R = 6378137     # earth radius
    x = R * math.radians(lon)
    y = R * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return x, y

def BFSTree(g):
    q = [g.vs[0]]
    visited = set()
    
    while len(q) > 0:
        for edge in g.incident(q.pop(0)):
            e = g.es[edge]
            if e.target not in visited:
                visited.add(e.target)
                e['BFSTree'] = True
                q.append(g.vs[e.target])

def load_graph(node_file, edge_file):
    g = ig.Graph()
    
    with open(node_file) as node_list:
        reader = csv.reader(node_list)
        for row in reader:
            g.add_vertex(name=row[1], country=row[2], lat=float(row[3]), lon=float(row[4]), population=int(row[5]), density=float(row[6]), hdi=float(row[7]))

    edge_list = pd.read_csv(edge_file, header=None)
    edge_list.columns = ['src', 'dest', 'weight', 'type']
    edges = list(zip(edge_list['src'] - 1, edge_list['dest'] - 1))
    
    g.add_edges(edges)
    g.es['weight'] = edge_list['weight'].tolist()
    g.es['type'] = edge_list['type'].tolist()
    
    BFSTree(g)
    return g

g = load_graph('data/node_list.csv', 'data/edge_list_type.csv')
app = Flask(__name__)
CORS(app)

@app.route('/graph')
def getGraph():
    nodes = []
    for v in g.vs:
        x, y = latlon_to_xy(v['lat'], v['lon'])
        nodes.append({
            'id': v.index,
            'x': x,
            'y': y,
            'size': 2,
            'fixed': True
        })
    
    # takes edges in a spanning tree + all airport edges
    edges = [
        {'from': e.source, 'to': e.target}
        for e in g.es if e['BFSTree'] or e['type'] == 'a'
    ]
    
    return jsonify({'nodes': nodes, 'edges': edges})

if __name__ == '__main__':
    app.run(debug=True)