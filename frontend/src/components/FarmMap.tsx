import { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { BoundaryGeoJSON } from '../types';

export type { BoundaryGeoJSON };

export interface LatLng {
  lat: number;
  lng: number;
}

const UZ_CENTER: [number, number] = [41.3, 64.5]; // Uzbekistan
const OSM_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const OSM_ATTR = '&copy; OpenStreetMap contributors';

/* --- pin icon (leaflet's default icon asset paths break in bundlers) --- */
const pinIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

function toLeafletRings(geo: BoundaryGeoJSON): [number, number][][] {
  // GeoJSON ring: [lng, lat] -> Leaflet: [lat, lng]
  if (geo?.type !== 'Polygon') return [];
  return (geo.coordinates as number[][][]).map((ring) =>
    ring.map(([lng, lat]) => [lat, lng] as [number, number])
  );
}

function centroidOf(geo: BoundaryGeoJSON | null): LatLng | null {
  if (!geo) return null;
  if (geo.type === 'Point') {
    const [lng, lat] = geo.coordinates as number[];
    return { lat, lng };
  }
  const rings = toLeafletRings(geo);
  const ring = rings[0] || [];
  if (!ring.length) return null;
  let lat = 0;
  let lng = 0;
  for (const [la, ln] of ring) {
    lat += la;
    lng += ln;
  }
  return { lat: lat / ring.length, lng: lng / ring.length };
}

function FitOnce({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 1) {
      map.setView(points[0], 15);
    } else if (points.length > 1) {
      map.fitBounds(L.latLngBounds(points).pad(0.25));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return null;
}

/** Draw mode: clicking adds vertices to the polygon; last vertex is draggable. */
function ClickDrawer({
  points,
  onAdd,
  onMoveLast,
}: {
  points: LatLng[];
  onAdd: (p: LatLng) => void;
  onMoveLast: (p: LatLng) => void;
}) {
  useMapEvents({
    click(e) {
      onAdd({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  if (points.length === 0) return null;
  const leafletPts: [number, number][] = points.map((p) => [p.lat, p.lng]);
  return (
    <>
      {leafletPts.length >= 3 && <Polygon positions={leafletPts} pathOptions={{ color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.25 }} />}
      {leafletPts.map((pos, i) =>
        i === leafletPts.length - 1 ? (
          <Marker
            key={i}
            position={pos}
            icon={pinIcon}
            draggable
            eventHandlers={{
              dragend: (e) => {
                const ll = (e.target as L.Marker).getLatLng();
                onMoveLast({ lat: ll.lat, lng: ll.lng });
              },
            }}
          />
        ) : (
          <Marker key={i} position={pos} icon={pinIcon} interactive={false} />
        )
      )}
    </>
  );
}

export function boundaryToGeoJSON(points: LatLng[]): BoundaryGeoJSON {
  // Leaflet [lat,lng] -> GeoJSON [lng,lat], auto-closing the ring
  const ring = points.map((p) => [p.lng, p.lat]);
  if (ring.length >= 3) {
    const [firstLng, firstLat] = ring[0];
    const [lastLng, lastLat] = ring[ring.length - 1];
    if (firstLng !== lastLng || firstLat !== lastLat) ring.push([firstLng, firstLat]);
    return { type: 'Polygon', coordinates: [ring] };
  }
  if (ring.length === 1) return { type: 'Point', coordinates: ring[0] };
  return { type: 'Point', coordinates: [] };
}

export function geoJSONToPoints(geo: BoundaryGeoJSON | null): LatLng[] {
  if (!geo) return [];
  if (geo.type === 'Point') {
    const [lng, lat] = (geo.coordinates as number[]) || [];
    return Number.isFinite(lat) && Number.isFinite(lng) ? [{ lat, lng }] : [];
  }
  return (toLeafletRings(geo)[0] || []).slice(0, -1).map(([lat, lng]) => ({ lat, lng }));
}

interface Props {
  /** existing boundary in edit mode */
  boundary?: BoundaryGeoJSON | null;
  /** draw mode with editable vertex list */
  drawPoints?: LatLng[];
  onMapClick?: (p: LatLng) => void;
  onMoveLast?: (p: LatLng) => void;
  className?: string;
}

export default function FarmMap({
  boundary,
  drawPoints,
  onMapClick,
  onMoveLast,
  className,
}: Props) {
  const center = useMemo(() => centroidOf(boundary ?? null), [boundary]);
  const drawMode = Boolean(onMapClick);

  if (drawMode && drawPoints) {
    return (
      <MapContainer
        center={center ? [center.lat, center.lng] : UZ_CENTER}
        zoom={center ? 13 : 6}
        className={className || 'w-full h-72 rounded-xl z-0'}
      >
        <TileLayer url={OSM_URL} attribution={OSM_ATTR} />
        <ClickDrawer points={drawPoints} onAdd={onMapClick!} onMoveLast={onMoveLast || (() => undefined)} />
        <FitOnce points={drawPoints.map((p) => [p.lat, p.lng])} />
      </MapContainer>
    );
  }

  // display mode
  const pts: [number, number][] = boundary
    ? toLeafletRings(boundary)[0] || (center ? [[center.lat, center.lng]] : [])
    : [];
  return (
    <MapContainer
      center={center ? [center.lat, center.lng] : UZ_CENTER}
      zoom={center ? 13 : 6}
      className={className || 'w-full h-72 rounded-xl z-0'}
    >
      <TileLayer url={OSM_URL} attribution={OSM_ATTR} />
      {boundary?.type === 'Polygon' && (
        <Polygon positions={pts} pathOptions={{ color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.25 }} />
      )}
      {center && <Marker position={[center.lat, center.lng]} icon={pinIcon} />}
      <FitOnce points={pts} />
    </MapContainer>
  );
}
