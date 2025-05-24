var map = L.map("map", {
    // zoomControl: false,
    minZoom: 2.95,
    maxBounds: [
        [75, -160],
        [-60, 179]
    ],
    zoomControl: false,
    zoomSnap: 0.01,
    wheelPxPerZoomLevel: 10,
    maxBoundsViscosity: 1
}).setView([25, 10], 2.95);  //  arbitrary default view

// map image
L.tileLayer(
    "https://api.maptiler.com/maps/satellite/{z}/{x}/{y}.jpg?key=pggU6bH00Uv4kVeMXDve",
    {
        attribution: '&copy; <a href="https://www.maptiler.com/">MapTiler</a>',
    }
).addTo(map);

// country borders
fetch(
"data/countries.geo.json"
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
    iconSize: [12, 12],
    iconAnchor: [6, 12]
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

const mapCountries = {}
function addCountryBorders(data, map) {
    L.geoJSON(data, {
        style: defNormalStyle(),
        onEachFeature: (feature, layer) => {
            mapCountries[feature.properties.name] = [feature, layer];
            feature.properties.q = false;
            feature.properties.normalStyle = defNormalStyle();
            feature.properties.highlightedStyle = defHighlightedStyle();
            addEvents(feature, layer);
        }
    }).addTo(map);
}

function defNormalStyle() {
    return {
                color: '#606060',
                weight: 1,
                fillOpacity: 0
            };
}

function defHighlightedStyle() {
    return {
                color: '#a0a0a0',
                weight: 2.5,
                fillOpacity: 0.2
            };
}

function addEvents(feature, layer) {
    layer.on({
        mouseover: (e) => countryHover(e, feature),
        mouseout: (e) => resetCountry(e, feature),
        click: () => countryClick(feature)
    });
}

const pop = document.querySelector(".heading");
const inf = document.getElementById("infected");
const recov = document.getElementById("recovered");
const dead = document.getElementById("dead");
function setInfo(country) {
    let name;
    if (country.length >= 20) {
        switch (country) {
            case "United States of America":
                name = 'USA';
                break;
            case "United Republic of Tanzani":
                name = 'Tanzania';
                break;
            case "Democratic Republic of the Congo":
                name = 'DR Congo';
                break;
            case "United Republic of Tanzania":
                name = "Tanzania";
                break;
            case "Central African Republic":
                name = 'Central Africa';
                break;
            case "Bosnia and Herzegovina":
                name = 'Bosnia';
                break;
            case "Republic of the Congo":
                name = 'Congo';
                break;
            case "United Arab Emirates":
                name = 'Arab Emirates';
                break;
            default:
                name = country;
                break;
        }
    } else
        name = country;

    try {
        pop.textContent = name + " - " + (countryInfo[country][3] - countryInfo[country][2]).toLocaleString();
        inf.textContent = countryInfo[country][0].toLocaleString();
        recov.textContent = countryInfo[country][1].toLocaleString();
        dead.textContent = countryInfo[country][2].toLocaleString();
    } catch (e) {
        console.log(country, e);
    }
}

let hoveredCountry = 'World';
function countryHover(e, feature) {
    hoveredCountry = feature.properties.name;
    e.target.setStyle(feature.properties.highlightedStyle);
    setInfo(feature.properties.name);
}

function resetCountry(e, feature) {
    e.target.setStyle(feature.properties.normalStyle);
    hoveredCountry = 'World';
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

    const n = data.startNode
    graph.setNodeAttribute(n.id, 'color', `rgba(${n.color[0]}, 0, ${n.color[2]}, ${n.color[1]})`);
    infectedNodes[n.id] = ({'lat': graph.getNodeAttribute(n.id, 'lat'), 'lon': graph.getNodeAttribute(n.id, 'lon'), 'radius': n.radius, 'color': `rgb(${n.color[0]}, ${n.color[2]}, 0)`});
    infectedLayer.setNodes(Object.values(infectedNodes));
}

function onSwitchTabClick(renderer) {
    mapDiv.classList.toggle("active")
    graphDiv.classList.toggle("active")
    if (graphDiv.classList.contains("active")) {
        switchTab.textContent = "Back to Map"
        setTimeout(() => {
            if (firstSwitch) {
                firstSwitch = false;
                clampCamera(renderer)
            }
            renderer.refresh();
        }, 100);
    } else {
        switchTab.textContent = "Show Underlying Graph"
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

const playPause = document.getElementById('play-pause');
const optionbg = document.getElementById('controls').style.backgroundColor
let state = false        // false -> paused
playPause.addEventListener('click', () => {
    speed1.style.backgroundColor = optionbg;
    speed2.style.backgroundColor =  optionbg;
    speed = speeds[0];
    if (!state) {
        state = !state;
        step();
        playPause.src = 'icons/pause.svg';
    } else {
        state = !state;
        playPause.src = 'icons/play.svg';
    }
});

const speeds = [2000, 1000, 600];
let speed = speeds[0];
const speed1 = document.getElementById('speed1');
const speed2 = document.getElementById('speed2');
speed1.addEventListener('click', () =>{
    speed = speeds[1];
    speed1.style.backgroundColor = 'rgba(128, 128, 128, 0.5)'
    speed2.style.backgroundColor = 'rgba(64, 64, 64, 0.5)'
});
speed2.addEventListener('click', () => {
    speed = speeds[2];
    speed1.style.backgroundColor = 'rgba(64, 64, 64, 0.5)'
    speed2.style.backgroundColor = 'rgba(128, 128, 128, 0.5)'
});

let stepData;
const dayDiv = document.getElementById('day')
let day = 0;
async function step() {
    // paused, dont do anything
    if (!state)
        return;


    if (stepData)
        updateNodes(stepData);

    try {
        const response = await fetch('http://localhost:5000/update');
        const data = await response.json();
        day += 1;
        dayDiv.textContent = `Day ${day}`
        stepData = data;
    } catch (err) {
        console.error(err);
    }

    // next fetch
    setTimeout(step, speed);
}

let infectedLayer = new InfectedLayer([], {});
map.addLayer(infectedLayer);
const infectedNodes = {};

const S = []
const E = []
const I = []
const R = []
const D = []
const V = []
function updateNodes(data) {
    countryInfo = data.countries;
    S.push(countryInfo['World'][5])
    E.push(countryInfo['World'][6])
    I.push(countryInfo['World'][0])
    R.push(countryInfo['World'][1])
    D.push(countryInfo['World'][2])
    V.push(countryInfo['World'][4])
    data.nodes.forEach(n => {
        graph.setNodeAttribute(n.id, 'color', `rgba(${n.color[0]}, 0, ${n.color[2]}, ${n.color[1]})`);
        if (!infectedNodes[n.id])
            infectedNodes[n.id] = ({'lat': graph.getNodeAttribute(n.id, 'lat'), 'lon': graph.getNodeAttribute(n.id, 'lon'), 'radius': n.radius, 'color': `rgb(${n.color[0]}, 0, ${n.color[2]})`});
        else {
            infectedNodes[n.id].color = `rgb(${n.color[0]}, 0, ${n.color[2]})`;
            infectedNodes[n.id].radius = n.radius;
        }
        if (n.radius == 0)
            delete infectedNodes[n.id];
    });
    infectedLayer.setNodes(Object.values(infectedNodes));
    data.edges.forEach(e => {
        highlightEdge(e);
    });
    if (data.quarantined != '') {
        const feature = mapCountries[data.quarantined][0];
        const layer = mapCountries[data.quarantined][1];
        if (feature.properties.q) {
            feature.properties.normalStyle = defNormalStyle();
            feature.properties.highlightedStyle = defHighlightedStyle();
            layer.setStyle(defNormalStyle());
        } else {
            const quarantineStyle = {
                color: '#daff45',
                weight: 2.5,
                fillOpacity: 0.4
            }
            feature.properties.normalStyle = quarantineStyle;
            feature.properties.highlightedStyle = {
                color: '#ccff00',
                weight: 3,
                fillOpacity: 0.5
            }
            layer.setStyle(quarantineStyle);
        }
        feature.properties.q = !feature.properties.q;
    }
    setInfo(hoveredCountry);
}

function highlightEdge(edge) {
    if (!graph.hasEdge(edge))
        return;

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
        if (!(src in airports) || !(dest in airports))
            return;
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

const chartButton = document.getElementById('chart-button');
chartButton.addEventListener('click', () => displayChart());
document.querySelector('.close').addEventListener('click', () => {
    document.getElementById('chart-container').style.display = 'none';
})

let chart = null;
function displayChart() {
    document.getElementById('chart-container').style.display = 'flex'
    const ctx = document.getElementById('linechart').getContext('2d');
    if (chart)
        chart.destroy();

    chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array.from({length: S.length}, (_, i) => i + 1),
            datasets: [
                {
                    label: 'Susceptible',
                    data: S,
                    borderColor: 'yellow',
                    fill: false,
                    tension: 2
                },
                {
                    label: 'Exposed',
                    data: E,
                    borderColor: 'green',
                    fill: false,
                    tension: 2
                },
                {
                    label: 'Infected',
                    data: I,
                    borderColor: 'red',
                    fill: false,
                    tension: 2
                },
                {
                    label: 'Recovered',
                    data: R,
                    borderColor: 'blue',
                    fill: false,
                    tension: 2
                },
                {
                    label: 'Dead',
                    data: D,
                    borderColor: 'gray',
                    fill: false,
                    tension: 2
                },
                {
                    label: 'Vaccinated',
                    data: V,
                    borderColor: 'purple',
                    fill: false,
                    tension: 2
                }
            ]
        }, options: {
            responsive: true,
            plugins: {
                legend: {position: 'top'},
                title: {display: true, text: 'Disease Spread'}
            }
        }
    });
}

document.getElementById('center').addEventListener('click', () => {
    map.setView([25, 10], 2.95);
});