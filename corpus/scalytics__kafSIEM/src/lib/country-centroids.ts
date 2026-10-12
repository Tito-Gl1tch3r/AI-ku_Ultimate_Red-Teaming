/*
 * kafSIEM — Approximate country centroids (ISO 3166-1 alpha-2).
 * Used to place alerts that carry an event country but no geocoded
 * coordinates, and to map country codes onto map regions.
 */

import { latLngToRegion, MIDDLE_EAST_CODES } from "@/lib/regions";
import type { Alert } from "@/types/alert";

export const COUNTRY_CENTROIDS: Record<string, [number, number]> = {
  AD: [42.5, 1.6], AE: [23.9, 54.3], AF: [33.9, 66.0], AG: [17.1, -61.8],
  AL: [41.1, 20.1], AM: [40.3, 45.0], AO: [-12.3, 17.5], AR: [-35.4, -65.1],
  AT: [47.6, 14.1], AU: [-25.7, 134.5], AZ: [40.3, 47.5], BA: [44.2, 17.8],
  BB: [13.2, -59.6], BD: [23.9, 90.2], BE: [50.6, 4.6], BF: [12.3, -1.8],
  BG: [42.8, 25.2], BH: [26.0, 50.5], BI: [-3.4, 29.9], BJ: [9.6, 2.3],
  BN: [4.5, 114.7], BO: [-16.7, -64.7], BR: [-10.8, -53.1], BS: [24.3, -76.6],
  BT: [27.4, 90.4], BW: [-22.2, 23.8], BY: [53.5, 28.0], BZ: [17.2, -88.7],
  CA: [61.4, -98.3], CD: [-2.9, 23.7], CF: [6.6, 20.5], CG: [-0.8, 15.2],
  CH: [46.8, 8.2], CI: [7.6, -5.6], CL: [-37.7, -71.4], CM: [5.7, 12.7],
  CN: [36.6, 103.8], CO: [3.9, -73.1], CR: [9.9, -84.2], CU: [21.6, -79.0],
  CV: [15.1, -23.6], CY: [35.0, 33.2], CZ: [49.7, 15.3], DE: [51.1, 10.4],
  DJ: [11.7, 42.6], DK: [56.0, 10.0], DM: [15.4, -61.4], DO: [18.9, -70.5],
  DZ: [28.2, 2.6], EC: [-1.4, -78.8], EE: [58.7, 25.5], EG: [26.5, 29.8],
  ER: [15.4, 38.8], ES: [40.2, -3.6], ET: [8.6, 39.6], FI: [64.5, 26.3],
  FJ: [-17.4, 178.0], FM: [7.5, 153.2], FR: [46.6, 2.5], GA: [-0.6, 11.8],
  GB: [54.2, -2.9], GD: [12.1, -61.7], GE: [42.2, 43.5], GH: [7.9, -1.2],
  GL: [74.7, -41.3], GM: [13.4, -15.4], GN: [10.4, -10.9], GQ: [1.7, 10.3],
  GR: [39.1, 22.9], GT: [15.7, -90.4], GW: [12.0, -14.9], GY: [4.8, -58.9],
  HN: [14.8, -86.6], HR: [45.1, 16.4], HT: [18.9, -72.7], HU: [47.2, 19.4],
  ID: [-2.2, 117.4], IE: [53.2, -8.1], IL: [31.4, 35.0], IN: [22.9, 79.6],
  IQ: [33.0, 43.7], IR: [32.6, 54.3], IS: [65.0, -18.6], IT: [42.8, 12.1],
  JM: [18.2, -77.3], JO: [31.2, 36.8], JP: [37.6, 138.0], KE: [0.5, 37.9],
  KG: [41.5, 74.5], KH: [12.7, 105.0], KI: [1.4, 173.0], KM: [-11.9, 43.7],
  KN: [17.3, -62.8], KP: [40.2, 127.2], KR: [36.4, 127.8], KW: [29.3, 47.6],
  KZ: [48.2, 67.3], LA: [18.5, 103.7], LB: [33.9, 35.9], LC: [13.9, -61.0],
  LI: [47.1, 9.6], LK: [7.6, 80.7], LR: [6.5, -9.3], LS: [-29.6, 28.2],
  LT: [55.3, 23.9], LU: [49.8, 6.1], LV: [56.9, 24.9], LY: [27.0, 18.0],
  MA: [31.9, -6.3], MC: [43.7, 7.4], MD: [47.2, 28.5], ME: [42.8, 19.2],
  MG: [-19.4, 46.7], MH: [7.0, 170.3], MK: [41.6, 21.7], ML: [17.3, -3.5],
  MM: [21.2, 96.5], MN: [46.8, 103.1], MR: [20.3, -10.3], MT: [35.9, 14.4],
  MU: [-20.2, 57.6], MV: [3.7, 73.2], MW: [-13.2, 34.3], MX: [23.9, -102.5],
  MY: [3.8, 109.7], MZ: [-17.3, 35.5], NA: [-22.1, 17.2], NE: [17.4, 9.4],
  NG: [9.6, 8.1], NI: [12.8, -85.0], NL: [52.1, 5.3], NO: [64.5, 12.7],
  NP: [28.3, 83.9], NR: [-0.5, 166.9], NZ: [-41.8, 171.5], OM: [20.6, 56.1],
  PA: [8.5, -80.1], PE: [-9.2, -74.4], PG: [-6.5, 145.2], PH: [11.8, 122.9],
  PK: [29.9, 69.4], PL: [52.1, 19.4], PS: [31.9, 35.2], PT: [39.6, -8.5],
  PW: [7.3, 134.4], PY: [-23.2, -58.4], QA: [25.3, 51.2], RO: [45.9, 25.0],
  RS: [44.2, 20.8], RU: [61.5, 105.3], RW: [-2.0, 29.9], SA: [24.1, 44.5],
  SB: [-8.9, 159.6], SC: [-4.7, 55.5], SD: [16.0, 30.0], SE: [62.8, 16.7],
  SG: [1.4, 103.8], SI: [46.1, 14.8], SK: [48.7, 19.5], SL: [8.6, -11.8],
  SM: [43.9, 12.5], SN: [14.4, -14.5], SO: [6.1, 45.9], SR: [4.1, -55.9],
  SS: [7.3, 30.2], ST: [0.4, 6.7], SV: [13.7, -88.9], SY: [35.0, 38.5],
  SZ: [-26.6, 31.5], TD: [15.4, 18.7], TG: [8.5, 1.0], TH: [15.1, 101.0],
  TJ: [38.5, 71.0], TL: [-8.8, 125.8], TM: [39.1, 59.4], TN: [34.1, 9.6],
  TO: [-20.4, -174.8], TR: [39.1, 35.2], TT: [10.5, -61.3], TV: [-8.5, 179.2],
  TW: [23.8, 121.0], TZ: [-6.3, 34.8], UA: [48.9, 31.4], UG: [1.3, 32.4],
  US: [39.8, -98.6], UY: [-32.8, -56.0], UZ: [41.7, 63.1], VA: [41.9, 12.5],
  VC: [13.2, -61.2], VE: [7.1, -66.2], VN: [16.6, 106.3], VU: [-16.2, 167.7],
  WS: [-13.8, -172.1], XK: [42.6, 20.9], YE: [15.9, 47.6], ZA: [-29.0, 25.1],
  ZM: [-13.5, 27.8], ZW: [-19.0, 29.9],
};

export function countryCentroid(code: string | undefined): [number, number] | null {
  if (!code) return null;
  return COUNTRY_CENTROIDS[code.trim().toUpperCase()] ?? null;
}

// withCentroidCoords places an ungeocoded alert at its event country's
// centroid so cluster members without coordinates (typical for cyber
// advisories) still appear on the map.
export function withCentroidCoords(alert: Alert): Alert {
  if (!(alert.lat === 0 && alert.lng === 0)) return alert;
  const centroid = countryCentroid(alert.event_country_code || alert.source.country_code);
  if (!centroid) return alert;
  return { ...alert, lat: centroid[0], lng: centroid[1] };
}

// countryRegion maps an ISO code onto the map's region filter vocabulary.
export function countryRegion(code: string | undefined): string | null {
  const normalized = (code ?? "").trim().toUpperCase();
  if (!normalized) return null;
  if (MIDDLE_EAST_CODES.has(normalized)) return "Middle East";
  const centroid = countryCentroid(normalized);
  if (!centroid) return null;
  return latLngToRegion(centroid[0], centroid[1]);
}
