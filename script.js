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

const airportIcon = L.icon({
    iconUrl: 'icons/airport.svg',
    iconSize: [16, 16],
    iconAnchor: [8, 16]
})

Papa.parse("data/filtered_airports.csv", {
    download: true,
    dynamicTyping: true,
    complete: (airports) => {
        airports.data.forEach(coords => {
            L.marker(coords, {icon: airportIcon}).addTo(map);
        });
    }
})

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
    }
}

function highlightedStyle() {
    return {
        fillOpacity: 1
    }
}

function addEvents(feature, layer) {
    layer.on({
        mouseover: highlightCountry,
        mouseout: resetCountry,
        click: () => countryClick(feature)
    })
}

function highlightCountry(e) {
    e.target.setStyle(highlightedStyle())
}

function resetCountry(e) {
    e.target.setStyle(borderStyle())
}

function countryClick(feature) {
    console.log(feature.properties.name)
}