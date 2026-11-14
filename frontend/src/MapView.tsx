import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Complaint } from './types';

export default function MapView({items}: {items: Complaint[]}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const layer = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!container.current || map.current) return;
    const m = L.map(container.current, { zoomControl: false, scrollWheelZoom: false }).setView([40.716, -73.95], 10);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }).addTo(m);
    L.control.zoom({position:'bottomright'}).addTo(m);
    map.current = m; layer.current = L.layerGroup().addTo(m);
    return () => { m.remove(); map.current = null; layer.current = null; };
  }, []);
  useEffect(() => {
    if (!layer.current) return;
    layer.current.clearLayers();
    items.forEach(c => {
      if (c.latitude === null || c.longitude === null) return;
      const isClosed = ['closed','resolved'].includes(c.status.toLowerCase());
      const circle = L.circleMarker([c.latitude,c.longitude], {
        radius: 6, color: '#ffffff', weight: 1.6, fillColor: isClosed ? '#879a90' : '#d87f52', fillOpacity: 0.94
      });
      // Leaflet popup text must not include raw externally supplied HTML.
      const safe = (s: string) => s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] || c));
      circle.bindPopup(`<strong>${safe(c.complaint_type)}</strong><br/>${safe(c.borough)}<br/>Status: ${safe(c.status)}`);
      circle.addTo(layer.current!);
    });
  }, [items]);
  return <div className="map" role="application" aria-label="Map showing complaint locations" ref={container}/>;
}
