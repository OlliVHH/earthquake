// Human: Build a geodesic circle polygon for map radius overlays (e.g. 100 km context).
// Agent: READS center lon/lat and radiusKm; RETURNS GeoJSON Feature<Polygon>.
export function createRadiusCircleGeoJson(
  longitude: number,
  latitude: number,
  radiusKm: number,
  steps = 64,
): GeoJSON.Feature<GeoJSON.Polygon> {
  const coordinates: [number, number][] = [];
  const latRad = (latitude * Math.PI) / 180;
  const kmPerDegLat = 111.32;
  const kmPerDegLon = 111.32 * Math.cos(latRad);

  for (let i = 0; i <= steps; i += 1) {
    const angle = (i / steps) * 2 * Math.PI;
    const dx = (radiusKm / kmPerDegLon) * Math.cos(angle);
    const dy = (radiusKm / kmPerDegLat) * Math.sin(angle);
    coordinates.push([longitude + dx, latitude + dy]);
  }

  return {
    type: "Feature",
    properties: { radius_km: radiusKm },
    geometry: {
      type: "Polygon",
      coordinates: [coordinates],
    },
  };
}
