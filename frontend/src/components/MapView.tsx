// src/components/MapView.tsx
import { useEffect, useRef, useImperativeHandle, forwardRef } from "react";

export type MapHandle = {
  dropMarker: (lat: number, lng: number, title?: string) => void;
  panTo: (lat: number, lng: number, zoom?: number) => void;
};

type Props = {
  center: google.maps.LatLngLiteral;
  zoom?: number;
  onReady?: () => void;
};

const MAP_STYLE: google.maps.MapTypeStyle[] = [
  { elementType:'geometry', stylers:[{color:'#f5f5f5'}] },
  { elementType:'labels.icon', stylers:[{visibility:'off'}] },
  { elementType:'labels.text.fill', stylers:[{color:'#616161'}] },
  { elementType:'labels.text.stroke', stylers:[{color:'#f5f5f5'}] },
  { featureType:'administrative.land_parcel', stylers:[{visibility:'off'}] },
  { featureType:'poi', stylers:[{visibility:'off'}] },
  { featureType:'road', elementType:'geometry', stylers:[{color:'#ffffff'}] },
  { featureType:'road.highway', elementType:'geometry', stylers:[{color:'#dadada'}] },
  { featureType:'transit', stylers:[{visibility:'off'}] },
  { featureType:'water', elementType:'geometry', stylers:[{color:'#c9e6ff'}] }
];

export const MapView = forwardRef<MapHandle, Props>(function MapView(
  { center, zoom = 16, onReady },
  ref
) {
  const divRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markerRef = useRef<google.maps.Marker | null>(null);

  useEffect(() => {
    const g = (window as any).google as typeof google | undefined;
    if (!g || !divRef.current) return;

    mapRef.current = new g.maps.Map(divRef.current, {
      center, zoom, styles: MAP_STYLE, mapTypeControl: false,
    });

    onReady?.();
  }, [center, zoom, onReady]);

  useImperativeHandle(ref, () => ({
    dropMarker(lat, lng, title) {
      const g = (window as any).google as typeof google | undefined;
      if (!g || !mapRef.current) return;
      if (markerRef.current) markerRef.current.setMap(null);
      markerRef.current = new g.maps.Marker({
        position: { lat, lng }, map: mapRef.current, title,
      });
      mapRef.current.panTo({ lat, lng });
      mapRef.current.setZoom(18);
    },
    panTo(lat, lng, z) {
      if (!mapRef.current) return;
      mapRef.current.panTo({ lat, lng });
      if (z) mapRef.current.setZoom(z);
    }
  }));

  return <div ref={divRef} className="map" role="application" aria-label="Campus map" />;
});
