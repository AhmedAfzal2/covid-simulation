// a class to efficiently draw infection markers
// simply adding one marker for each city causes major problems beyond ~500 nodes
// this class draws all markers as one layer
class InfectedLayer extends L.Layer {
  constructor(options = {}) {
    super();
    this.nodes = [];
    this.options = options;
  }

  onAdd(map) {
    this._map = map;
    this._canvas = L.DomUtil.create('canvas', 'leaflet-infected-layer');
    this._ctx = this._canvas.getContext('2d');

    const size = map.getSize();
    this._canvas.width = size.x;
    this._canvas.height = size.y;

    map.getPanes().overlayPane.appendChild(this._canvas);

    map.on('move resize zoom', this._reset, this);
    this._reset();
  }

  onRemove(map) {
    map.getPanes().overlayPane.removeChild(this._canvas);
    map.off('move resize zoom', this._reset, this);
  }

  // takes nodes as {lat: a, lon: b, radius: c}
  setNodes(nodes) {
    this.nodes = nodes;
    this._reset();
  }

  _reset = () => {
    const map = this._map;
    const size = map.getSize();

    this._canvas.width = size.x;
    this._canvas.height = size.y;

    const ctx = this._ctx;
    ctx.clearRect(0, 0, size.x, size.y);
    ctx.fillStyle = this.options.color || 'red';

    for (const node of this.nodes) {
      const point = map.latLngToContainerPoint([node.lat, node.lon]);
      ctx.beginPath();
      ctx.arc(point.x, point.y, node.radius, 0, Math.PI * 2);
      ctx.fill();
    }
  };
}