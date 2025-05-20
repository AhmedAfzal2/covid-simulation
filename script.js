var map = L.map("map", {
    zoomControl: false,
    dragging: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    touchZoom: false,
    zoomSnap: 0.1,
}).setView([25, 10], 2.9);  // arbitrary default view

// map image
L.tileLayer(
    "https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=pggU6bH00Uv4kVeMXDve",
    {
        attribution: '&copy; <a href="https://www.maptiler.com/">MapTiler</a>',
    }
).addTo(map);

// country borders
fetch(
"https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
)
    .then((response) => response.json())
    .then((data) => {
        addCountryBorders(data, map);
});

let countryInfo = {};
// graph data
fetch('http://localhost:5000/graph')
    .then(response => response.json())
    .then(data => {
        drawGraph(data);
        countryInfo = data.countries;
        setInfo('World');
    });

const airportIcon = L.icon({
    iconUrl: 'icons/airport.svg',
    iconSize: [16, 16],
    iconAnchor: [8, 16]
});

const airports = {}
Papa.parse("data/filtered_airport_coords.csv", {
    download: true,
    dynamicTyping: true,
    complete: (file) => {
        file.data.forEach(airport => {
            const coords = [airport[1], airport[2]];
            airports[airport[0] - 1] = coords;          // -1 to align data file and backend ids
            L.marker(coords, {icon: airportIcon, interactive: false}).addTo(map);
        });
    }
});

function addCountryBorders(data, map) {
    L.geoJSON(data, {
        style: borderStyle(),
        onEachFeature: addEvents
    }).addTo(map);
}

function borderStyle() {
    return {
        color: '#606060',
        weight: 1,
        fillOpacity: 0
    };
}

function highlightedStyle() {
    return {
        fillOpacity: 1
    };
}

function addEvents(feature, layer) {
    layer.on({
        mouseover: (e) => countryHover(e, feature),
        mouseout: resetCountry,
        click: () => countryClick(feature)
    });
}

function highlightCountry(e) {
    e.target.setStyle(highlightedStyle());
}

function setInfo(country) {
    const pop = document.querySelector(".heading");
    const inf = document.getElementById("infected");
    const recov = document.getElementById("recovered");
    const dead = document.getElementById("dead");

    pop.textContent = country + " - " + (countryInfo[country][3] - countryInfo[country][2]).toLocaleString();
    inf.textContent = countryInfo[country][0].toLocaleString();
    recov.textContent = countryInfo[country][1].toLocaleString();
    dead.textContent = countryInfo[country][2].toLocaleString();
}

function countryHover(e, feature) {
    highlightCountry(e);
    setInfo(feature.properties.name);
}

function resetCountry(e) {
    e.target.setStyle(borderStyle());
    setInfo('World');
}

function countryClick(feature) {
    console.log(feature.properties.name);
    console.log(countryInfo[feature.properties.name])
}

const switchTab = document.getElementById('switch-tab');
const mapDiv = document.getElementById('map');
const graphDiv = document.getElementById('graph');
const graph = new graphology.Graph();
const countries = {}
let firstSwitch = true;

// creates graph and initializes renderer
function drawGraph(data) {
    data.nodes.forEach(n => {
        graph.addNode(n.id, n, {'color': '#ffffff'});
    });

    data.edges.forEach(e => {
        try {
            graph.addEdgeWithKey(e.id, e.from, e.to, {'color': 'rgb(37, 58, 109)'});
        }
        catch {}
    });

    const renderer = new Sigma(graph, graphDiv, {
        allowInvalidContainer: true,
        mouseEnabled: false
    });

    switchTab.addEventListener('click', () => {
        onSwitchTabClick(renderer)
    });

    graph.setNodeAttribute(3901, 'color', '#ff0000')
}

function onSwitchTabClick(renderer) {
    mapDiv.classList.toggle("active")
    graphDiv.classList.toggle("active")
    if (graphDiv.classList.contains("active")) {
        setTimeout(() => {
            if (firstSwitch) {
                firstSwitch = false;
                clampCamera(renderer)
            }
            renderer.refresh();
        }, 100);
    }
}

// fix the camera in one spot
function clampCamera(renderer) {
    // const camera = renderer.getCamera();
    // camera.setState({
    //         x: 0.492,
    //         y: 0.533
    //     });
    // camera.on("updated", () => {
    //     camera.setState({
    //         x: 0.492,
    //         y: 0.533,
    //         ratio: 1
    //     });
    // });
}

const step = document.getElementById('step');

step.addEventListener('click', () => {
    fetch('http://localhost:5000/update')
        .then(response => response.json())
        .then(data => {
            updateNodes(data);
        });
});

let infectedLayer = new InfectedLayer([], {});
map.addLayer(infectedLayer);
const infectedNodes = {};

function updateNodes(data) {
    countryInfo = data.countries;
    data.nodes.forEach(n => {
        graph.setNodeAttribute(n.id, 'color', `rgba(${n.color[0]}, 0, 0, ${n.color[1]})`);
        if (!infectedNodes[n.id])
            infectedNodes[n.id] =({'lat': graph.getNodeAttribute(n.id, 'lat'), 'lon': graph.getNodeAttribute(n.id, 'lon'), 'radius': n.radius});
    });
    infectedLayer.setNodes(Object.values(infectedNodes));
    data.edges.forEach(e => {
        highlightEdge(e);
    });
    setInfo('World');
}

function highlightEdge(edge) {
    if (!graph.hasEdge(edge))
        return

    if (graphDiv.classList.contains('active')) {
        graph.setEdgeAttribute(edge, 'color', '#00ffff');
        graph.setEdgeAttribute(edge, 'size', 2.5);
        setTimeout(() => {
            graph.setEdgeAttribute(edge, 'color', 'rgb(37, 58, 109)');
            graph.setEdgeAttribute(edge, 'size', 1);
        }, 500);
    } else {
        const src = graph.source(edge);
        const dest = graph.target(edge);
        const line = L.polyline([airports[src], airports[dest]], {
            color: '#00ffff',
            weight: 1,
            opacity: 1,
            smoothFactor: 1
        }).addTo(map);
        setTimeout(() => {
            line.remove();
        }, 500);
    }
}