/**
 * Utility geografiche per il calcolo delle distanze tra coordinate GPS.
 *
 * Fornisce `haversineDistanceMeters`, che calcola la distanza ortodromica
 * (grande cerchio) in metri tra due punti usando la formula di Haversine e il
 * raggio terrestre medio. Usata per distanze, segmenti e statistiche dei ride.
 *
 * Calculates the great-circle distance between two points on a sphere
 * given their longitudes and latitudes.
 *
 * @param lat1 Latitude of point 1 (in degrees)
 * @param lon1 Longitude of point 1 (in degrees)
 * @param lat2 Latitude of point 2 (in degrees)
 * @param lon2 Longitude of point 2 (in degrees)
 * @returns Distance in meters
 */
export function haversineDistanceMeters(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const radius = 6371000; // Earth's radius in meters
  const toRadians = (value: number) => (value * Math.PI) / 180;

  const dLat = toRadians(lat2 - lat1);
  const dLon = toRadians(lon2 - lon1);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(lat1)) *
      Math.cos(toRadians(lat2)) *
      Math.sin(dLon / 2) ** 2;

  return 2 * radius * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
