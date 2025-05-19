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

// graph data
fetch('http://localhost:5000/graph')
    .then(response => response.json())
    .then(data => {
        drawGraph(data);
    });

const airportIcon = L.icon({
    iconUrl: 'icons/airport.svg',
    iconSize: [16, 16],
    iconAnchor: [8, 16]
});

Papa.parse("data/filtered_airport_coords.csv", {
    download: true,
    dynamicTyping: true,
    complete: (airports) => {
        airports.data.forEach(coords => {
            L.marker(coords, {icon: airportIcon}).addTo(map);
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
        color: 'red',
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
        mouseover: highlightCountry,
        mouseout: resetCountry,
        click: () => countryClick(feature)
    });
}

function highlightCountry(e) {
    e.target.setStyle(highlightedStyle());
}

function resetCountry(e) {
    e.target.setStyle(borderStyle());
}

function countryClick(feature) {
    console.log(feature.properties.name);
}

const switchTab = document.getElementById('switch-tab');
const mapDiv = document.getElementById('map');
const graphDiv = document.getElementById('graph');
const graph = new graphology.Graph();
let firstSwitch = true;

// creates graph and initializes renderer
function drawGraph(data) {
    data.nodes.forEach(n => {
        graph.addNode(n.id, n);
    });
    data.edges.forEach(e => {
        try {
            graph.addEdgeWithKey(e.id, e.from, e.to);
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
            data.nodes.forEach(n => {
                graph.setNodeAttribute(n.id, 'color', n.color);
            })
        });
});