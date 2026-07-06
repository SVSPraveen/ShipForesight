import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// ─── Global City Coordinate Database ─────────────────────────────────────────
const CITY_COORDS = {
  // Americas
  'new york': [40.7128, -74.006], 'los angeles': [34.0522, -118.2437],
  'chicago': [41.8781, -87.6298], 'houston': [29.7604, -95.3698],
  'miami': [25.7617, -80.1918], 'dallas': [32.7767, -96.797],
  'seattle': [47.6062, -122.3321], 'san francisco': [37.7749, -122.4194],
  'toronto': [43.6532, -79.3832], 'montreal': [45.5017, -73.5673],
  'vancouver': [49.2827, -123.1207], 'mexico city': [19.4326, -99.1332],
  'sao paulo': [-23.5505, -46.6333], 'rio de janeiro': [-22.9068, -43.1729],
  'buenos aires': [-34.6037, -58.3816], 'bogota': [4.711, -74.0721],
  'lima': [-12.0464, -77.0428], 'santiago': [-33.4489, -70.6693],
  // Europe
  'london': [51.5074, -0.1278], 'paris': [48.8566, 2.3522],
  'amsterdam': [52.3676, 4.9041], 'rotterdam': [51.9244, 4.4777],
  'hamburg': [53.5753, 10.0153], 'berlin': [52.52, 13.405],
  'frankfurt': [50.1109, 8.6821], 'munich': [48.1351, 11.582],
  'antwerp': [51.2194, 4.4025], 'brussels': [50.8503, 4.3517],
  'madrid': [40.4168, -3.7038], 'barcelona': [41.3851, 2.1734],
  'rome': [41.9028, 12.4964], 'milan': [45.4654, 9.1859],
  'istanbul': [41.0082, 28.9784], 'athens': [37.9838, 23.7275],
  'vienna': [48.2082, 16.3738], 'zurich': [47.3769, 8.5417],
  'stockholm': [59.3293, 18.0686], 'oslo': [59.9139, 10.7522],
  'copenhagen': [55.6761, 12.5683], 'helsinki': [60.1699, 24.9384],
  'lisbon': [38.7169, -9.1395], 'dublin': [53.3498, -6.2603],
  'warsaw': [52.2297, 21.0122], 'prague': [50.0755, 14.4378],
  // Middle East
  'dubai': [25.2048, 55.2708], 'abu dhabi': [24.4539, 54.3773],
  'riyadh': [24.7136, 46.6753], 'jeddah': [21.4858, 39.1925],
  'doha': [25.2854, 51.531], 'kuwait city': [29.3759, 47.9774],
  'muscat': [23.5882, 58.3829], 'manama': [26.2235, 50.5876],
  'tel aviv': [32.0853, 34.7818], 'beirut': [33.8938, 35.5018],
  'tehran': [35.6892, 51.389], 'baghdad': [33.3152, 44.3661],
  'amman': [31.9454, 35.9284], 'ankara': [39.9334, 32.8597],
  // Africa
  'cairo': [30.0444, 31.2357], 'nairobi': [-1.2921, 36.8219],
  'johannesburg': [-26.2041, 28.0473], 'cape town': [-33.9249, 18.4241],
  'lagos': [6.5244, 3.3792], 'accra': [5.56, -0.1969],
  'addis ababa': [9.03, 38.74], 'dar es salaam': [-6.7924, 39.2083],
  'mombasa': [-4.0435, 39.6682], 'kampala': [0.3476, 32.5825],
  'khartoum': [15.5007, 32.5599], 'casablanca': [33.5731, -7.5898],
  'tunis': [36.8065, 10.1815], 'algiers': [36.7372, 3.0865],
  'kenya': [-1.2921, 36.8219], 'ethiopia': [9.03, 38.74],
  'tanzania': [-6.3690, 34.8888], 'ghana': [7.9465, -1.0232],
  'nigeria': [9.0820, 8.6753], 'south africa': [-30.5595, 22.9375],
  // South Asia — India (comprehensive)
  'mumbai': [19.076, 72.8777], 'delhi': [28.6139, 77.209],
  'new delhi': [28.6139, 77.209], 'chennai': [13.0827, 80.2707],
  'kolkata': [22.5726, 88.3639], 'bangalore': [12.9716, 77.5946],
  'bengaluru': [12.9716, 77.5946], 'hyderabad': [17.385, 78.4867],
  'pune': [18.5204, 73.8567], 'ahmedabad': [23.0225, 72.5714],
  'kochi': [9.9312, 76.2673], 'surat': [21.1702, 72.8311],
  'jaipur': [26.9124, 75.7873], 'lucknow': [26.8467, 80.9462],
  'noida': [28.5355, 77.3910], 'gurgaon': [28.4595, 77.0266],
  'gurugram': [28.4595, 77.0266], 'kanpur': [26.4499, 80.3319],
  'nagpur': [21.1458, 79.0882], 'indore': [22.7196, 75.8577],
  'thane': [19.2183, 72.9781], 'bhopal': [23.2599, 77.4126],
  'visakhapatnam': [17.6868, 83.2185], 'vizag': [17.6868, 83.2185],
  'patna': [25.5941, 85.1376], 'vadodara': [22.3072, 73.1812],
  'ludhiana': [30.9010, 75.8573], 'agra': [27.1767, 78.0081],
  'nashik': [19.9975, 73.7898], 'faridabad': [28.4089, 77.3178],
  'meerut': [28.9845, 77.7064], 'rajkot': [22.3039, 70.8022],
  'kalyan': [19.2437, 73.1355], 'vasai': [19.4680, 72.8375],
  'varanasi': [25.3176, 82.9739], 'srinagar': [34.0837, 74.7973],
  'aurangabad': [19.8762, 75.3433], 'dhanbad': [23.7957, 86.4304],
  'amritsar': [31.6340, 74.8723], 'navi mumbai': [19.0368, 73.0158],
  'allahabad': [25.4358, 81.8463], 'prayagraj': [25.4358, 81.8463],
  'howrah': [22.5958, 88.2636], 'ranchi': [23.3441, 85.3096],
  'coimbatore': [11.0168, 76.9558], 'jabalpur': [23.1815, 79.9864],
  'gwalior': [26.2183, 78.1828], 'vijayawada': [16.5062, 80.6480],
  'jodhpur': [26.2389, 73.0243], 'raipur': [21.2514, 81.6296],
  'kota': [25.2138, 75.8648], 'chandigarh': [30.7333, 76.7794],
  'guwahati': [26.1445, 91.7362], 'thiruvananthapuram': [8.5241, 76.9366],
  'trivandrum': [8.5241, 76.9366], 'solapur': [17.6599, 75.9064],
  'tiruchirappalli': [10.7905, 78.7047], 'mysore': [12.2958, 76.6394],
  'mysuru': [12.2958, 76.6394], 'bareilly': [28.3670, 79.4304],
  'aligarh': [27.8974, 78.0880], 'moradabad': [28.8386, 78.7733],
  'tiruppur': [11.1085, 77.3411], 'salem': [11.6643, 78.1460],
  'warangal': [17.9784, 79.6009], 'guntur': [16.3067, 80.4365],
  'hubli': [15.3647, 75.1240], 'mangalore': [12.9141, 74.8560],
  'mangaluru': [12.9141, 74.8560], 'tirunelveli': [8.7139, 77.7567],
  'dehradun': [30.3165, 78.0322], 'jammu': [32.7266, 74.8570],
  'shimla': [31.1048, 77.1734], 'nanded': [19.1383, 77.3210],
  'kolhapur': [16.7050, 74.2433], 'akola': [20.7002, 77.0082],
  'latur': [18.4088, 76.5604], 'gandhinagar': [23.2156, 72.6369],
  'anand': [22.5645, 72.9289], 'rajpur': [22.3039, 70.8022],
  'karachi': [24.8608, 67.0104], 'lahore': [31.5204, 74.3587],
  'dhaka': [23.8103, 90.4125], 'colombo': [6.9271, 79.8612],
  'kathmandu': [27.7172, 85.324], 'india': [20.5937, 78.9629],
  'pakistan': [30.3753, 69.3451], 'bangladesh': [23.685, 90.3563],
  // East & Southeast Asia
  'shanghai': [31.2304, 121.4737], 'beijing': [39.9042, 116.4074],
  'shenzhen': [22.5431, 114.0579], 'guangzhou': [23.1291, 113.2644],
  'tianjin': [39.3434, 117.3616], 'hong kong': [22.3193, 114.1694],
  'singapore': [1.3521, 103.8198], 'kuala lumpur': [3.139, 101.6869],
  'bangkok': [13.7563, 100.5018], 'ho chi minh city': [10.8231, 106.6297],
  'hanoi': [21.0285, 105.8542], 'jakarta': [-6.2088, 106.8456],
  'manila': [14.5995, 120.9842], 'taipei': [25.033, 121.5654],
  'tokyo': [35.6762, 139.6503], 'osaka': [34.6937, 135.5023],
  'seoul': [37.5665, 126.978], 'busan': [35.1796, 129.0756],
  'china': [35.8617, 104.1954],
  // Oceania
  'sydney': [-33.8688, 151.2093], 'melbourne': [-37.8136, 144.9631],
  'brisbane': [-27.4698, 153.0251], 'perth': [-31.9505, 115.8605],
  'auckland': [-36.8485, 174.7633],
  // Country fallbacks
  'usa': [37.0902, -95.7129], 'us': [37.0902, -95.7129],
  'germany': [51.1657, 10.4515], 'france': [46.2276, 2.2137],
  'uk': [51.5, -0.12], 'saudi': [24.7136, 46.6753],
  'saudi arabia': [24.7136, 46.6753], 'uae': [25.2048, 55.2708],
  'japan': [36.2048, 138.2529], 'south korea': [35.9078, 127.7669],
  'australia': [-25.2744, 133.7751], 'brazil': [-14.235, -51.9253],
  'indonesia': [-0.7893, 113.9213], 'malaysia': [4.2105, 101.9758],
  'thailand': [15.87, 100.9925], 'philippines': [12.8797, 121.774],
};

// ─── Key sea-lane waypoints (lat, lon) ──────────────────────────────────────
const WAYPOINTS = {
  // Strait of Gibraltar - Atlantic/Mediterranean entry
  GIBRALTAR: [35.98, -5.45],
  // Mediterranean midpoint
  MED_CENTER: [35.5, 18.0],
  // Suez Canal (Port Said north, Suez south)
  SUEZ_NORTH: [31.25, 32.33],
  SUEZ_SOUTH: [29.94, 32.55],
  // Red Sea entry/exit
  BAB_EL_MANDEB: [12.58, 43.47],
  // Gulf of Aden
  ADEN: [12.78, 45.02],
  // Arabian Sea
  ARABIAN_SEA: [15.0, 65.0],
  // Strait of Hormuz
  HORMUZ: [26.56, 56.46],
  // Indian Ocean center
  INDIAN_OCEAN_W: [-5.0, 60.0],
  INDIAN_OCEAN_E: [-5.0, 90.0],
  // Strait of Malacca
  MALACCA_W: [5.5, 99.5],
  MALACCA_E: [1.2, 104.5],
  // South China Sea
  SOUTH_CHINA_SEA: [12.0, 115.0],
  // Cape of Good Hope
  CAPE_GOOD_HOPE: [-34.5, 20.0],
  // Cape Horn
  CAPE_HORN: [-55.9, -67.3],
  // Panama Canal
  PANAMA_ATLANTIC: [9.38, -79.9],
  PANAMA_PACIFIC: [8.9, -79.5],
  // North Atlantic
  N_ATLANTIC_MID: [48.0, -30.0],
  // North Pacific
  N_PACIFIC_MID: [45.0, 180.0],
  N_PACIFIC_MID2: [45.0, -170.0],
  // South Pacific
  S_PACIFIC_MID: [-30.0, -130.0],
  // Australia/NZ area
  AUSTRALIA_W: [-25.0, 110.0],
  AUSTRALIA_S: [-40.0, 145.0],
};

// ─── Determine broad geographic region from lat/lon ──────────────────────────
function getRegion(lat, lon) {
  if (lon >= 100 && lat >= 20) return 'east_asia';           // China, Japan, Korea, Taiwan
  if (lon >= 95 && lat < 20 && lat > -15) return 'sea';     // SE Asia
  if (lon >= 60 && lon < 100 && lat > -10) return 'south_asia'; // India, Pakistan, Sri Lanka
  if (lon >= 30 && lon < 70 && lat >= 10 && lat < 40) return 'middle_east'; // Gulf, Saudi
  if (lon >= -15 && lon < 55 && lat >= 30) return 'europe';  // Europe including Turkey
  if (lon >= -20 && lon < 55 && lat < 30) return 'africa';   // Africa
  if (lon >= 110 && lat < -10) return 'australia';           // Australia
  if (lon >= -130 && lon < -60 && lat >= 15) return 'north_america';
  if (lon >= -85 && lon < -30 && lat < 15) return 'south_america';
  if (lon >= -130 && lon < -30 && lat < 15) return 'south_america';
  return 'other';
}

// ─── Build realistic ocean waypoints based on region pair ───────────────────
function getOceanWaypoints(startCoords, endCoords) {
  const [sLat, sLon] = startCoords;
  const [eLat, eLon] = endCoords;
  const sReg = getRegion(sLat, sLon);
  const eReg = getRegion(eLat, eLon);

  const W = WAYPOINTS;

  // East Asia ↔ Europe: Malacca → Indian Ocean → Suez → Mediterranean
  if ((sReg === 'east_asia' || sReg === 'sea') && eReg === 'europe') {
    return [W.MALACCA_W, W.INDIAN_OCEAN_W, W.ADEN, W.BAB_EL_MANDEB, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER];
  }
  if (sReg === 'europe' && (eReg === 'east_asia' || eReg === 'sea')) {
    return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.BAB_EL_MANDEB, W.ADEN, W.INDIAN_OCEAN_W, W.MALACCA_W];
  }

  // South Asia ↔ Europe: Arabian Sea → Red Sea → Suez → Mediterranean
  if (sReg === 'south_asia' && eReg === 'europe') {
    return [W.ARABIAN_SEA, W.ADEN, W.BAB_EL_MANDEB, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER];
  }
  if (sReg === 'europe' && eReg === 'south_asia') {
    return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.BAB_EL_MANDEB, W.ADEN, W.ARABIAN_SEA];
  }

  // Middle East ↔ Europe: via Suez
  if (sReg === 'middle_east' && eReg === 'europe') {
    // Gulf ports via Hormuz → Aden → Suez
    if (sLon > 50) return [W.HORMUZ, W.ARABIAN_SEA, W.ADEN, W.BAB_EL_MANDEB, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER];
    // Red Sea ports direct to Suez
    return [W.BAB_EL_MANDEB, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER];
  }
  if (sReg === 'europe' && eReg === 'middle_east') {
    if (eLon > 50) return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.BAB_EL_MANDEB, W.ADEN, W.ARABIAN_SEA, W.HORMUZ];
    return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.BAB_EL_MANDEB];
  }

  // East Asia ↔ North America: Trans-Pacific route
  if ((sReg === 'east_asia' || sReg === 'sea') && sReg !== eReg && eReg === 'north_america') {
    return sLon > 120 ? [W.N_PACIFIC_MID, W.N_PACIFIC_MID2] : [W.MALACCA_E, [10, 140], W.N_PACIFIC_MID, W.N_PACIFIC_MID2];
  }
  if (sReg === 'north_america' && (eReg === 'east_asia' || eReg === 'sea')) {
    return [[50, -170], W.N_PACIFIC_MID, [10, 140]];
  }

  // South America ↔ Everything: via Panama or Cape Horn
  if (sReg === 'south_america' && eReg === 'east_asia') {
    // Pacific coast can go direct, Atlantic coast needs Panama
    if (sLon < -70) return [W.PANAMA_PACIFIC, [10, 140], W.N_PACIFIC_MID2];
    return [W.CAPE_HORN, W.S_PACIFIC_MID, [10, 140]];
  }
  if (sReg === 'south_america' && eReg === 'europe') {
    return [[0, -30], W.N_ATLANTIC_MID];
  }

  // Africa ↔ East Asia: via Cape of Good Hope → Indian Ocean → Malacca
  if (sReg === 'africa' && (eReg === 'east_asia' || eReg === 'sea')) {
    return [W.CAPE_GOOD_HOPE, W.INDIAN_OCEAN_W, W.INDIAN_OCEAN_E, W.MALACCA_W];
  }
  if ((sReg === 'east_asia' || sReg === 'sea') && eReg === 'africa') {
    return [W.MALACCA_W, W.INDIAN_OCEAN_E, W.INDIAN_OCEAN_W, W.CAPE_GOOD_HOPE];
  }

  // Africa ↔ Europe: Atlantic coast or via Suez
  if (sReg === 'africa' && eReg === 'europe') {
    if (sLon > 35) return [W.BAB_EL_MANDEB, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER]; // East Africa
    return [[20, -10], W.GIBRALTAR]; // West Africa - up the Atlantic
  }
  if (sReg === 'europe' && eReg === 'africa') {
    if (eLon > 35) return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.BAB_EL_MANDEB];
    return [W.GIBRALTAR, [20, -10]];
  }

  // Africa ↔ South Asia: via Indian Ocean
  if (sReg === 'africa' && eReg === 'south_asia') {
    if (sLon > 35) return [W.INDIAN_OCEAN_W]; // East Africa
    return [W.CAPE_GOOD_HOPE, W.INDIAN_OCEAN_W];
  }
  if (sReg === 'south_asia' && eReg === 'africa') {
    if (eLon > 35) return [W.INDIAN_OCEAN_W];
    return [W.INDIAN_OCEAN_W, W.CAPE_GOOD_HOPE];
  }

  // Europe ↔ North America: North Atlantic
  if (sReg === 'europe' && eReg === 'north_america') {
    return [W.GIBRALTAR, W.N_ATLANTIC_MID];
  }
  if (sReg === 'north_america' && eReg === 'europe') {
    return [W.N_ATLANTIC_MID, W.GIBRALTAR];
  }

  // Australia ↔ Asia: via Malacca or direct
  if (sReg === 'australia' && (eReg === 'east_asia' || eReg === 'sea')) {
    return [W.AUSTRALIA_W, W.MALACCA_W];
  }
  if ((eReg === 'east_asia' || eReg === 'sea') && sReg === 'australia') {
    return [W.MALACCA_W, W.AUSTRALIA_W];
  }

  // Australia ↔ Europe
  if (sReg === 'australia' && eReg === 'europe') {
    return [W.AUSTRALIA_W, W.INDIAN_OCEAN_E, W.INDIAN_OCEAN_W, W.ADEN, W.SUEZ_SOUTH, W.SUEZ_NORTH, W.MED_CENTER];
  }
  if (sReg === 'europe' && eReg === 'australia') {
    return [W.MED_CENTER, W.SUEZ_NORTH, W.SUEZ_SOUTH, W.ADEN, W.INDIAN_OCEAN_W, W.INDIAN_OCEAN_E, W.AUSTRALIA_W];
  }

  // East Africa ↔ Middle East: Red Sea direct
  if (sReg === 'africa' && sLon > 35 && eReg === 'middle_east') {
    return [W.BAB_EL_MANDEB, W.ADEN, W.ARABIAN_SEA];
  }

  // Fallback: no specific waypoints, just connect
  return [];
}

// ─── Build interpolated line through waypoints ─────────────────────────────
function buildRoute(start, waypoints, end, steps = 6) {
  const points = [start, ...waypoints, end];
  const result = [];
  for (let i = 0; i < points.length - 1; i++) {
    const [lat1, lon1] = points[i];
    const [lat2, lon2] = points[i + 1];
    for (let s = 0; s <= steps; s++) {
      const t = s / steps;
      result.push([lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t]);
    }
  }
  return result;
}

// ─── Geocoding ───────────────────────────────────────────────────────────────
function lookupCity(city) {
  const key = city.toLowerCase().trim();
  if (CITY_COORDS[key]) return CITY_COORDS[key];
  for (const [k, v] of Object.entries(CITY_COORDS)) {
    if (k.includes(key) || key.includes(k)) return v;
  }
  return null;
}

async function getCityCoords(city, countryCode) {
  const cached = lookupCity(city);
  if (cached) return cached;
  try {
    await new Promise(r => setTimeout(r, 300));
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(city + ' ' + countryCode)}&format=json&limit=1`;
    const res = await fetch(url, { headers: { 'User-Agent': 'ShipForesight/1.0' } });
    if (res.ok) {
      const data = await res.json();
      if (data?.length > 0) {
        const coords = [parseFloat(data[0].lat), parseFloat(data[0].lon)];
        CITY_COORDS[key] = coords;
        return coords;
      }
    }
  } catch (e) {}
  return null;
}

// ─── Map auto-fit ─────────────────────────────────────────────────────────────
function MapUpdater({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords?.length >= 2) {
      try { map.fitBounds(L.latLngBounds(coords), { padding: [40, 40] }); } catch (e) {}
    }
  }, [coords, map]);
  return null;
}

const ROUTE_COLORS = { FTL: '#D97706', LTL: '#D97706', Intermodal: '#7C3AED', Ocean: '#0F766E', Air: '#2563EB' };

// ─── Main Component ───────────────────────────────────────────────────────────
export default function MapWidget({ originCity, originCountry, destCity, destCountry, carrierType }) {
  const [state, setState] = useState({ origin: null, dest: null, route: [], routeType: '', loading: true, error: null });

  useEffect(() => {
    let active = true;
    setState(s => ({ ...s, loading: true, error: null }));

    const run = async () => {
      const start = await getCityCoords(originCity, originCountry);
      const end = await getCityCoords(destCity, destCountry);
      if (!active) return;

      if (!start) return setState(s => ({ ...s, loading: false, error: `Cannot find "${originCity}". Try a nearby major city.` }));
      if (!end) return setState(s => ({ ...s, loading: false, error: `Cannot find "${destCity}". Try a nearby major city.` }));

      const isRoad = ['FTL', 'LTL', 'Intermodal'].includes(carrierType);
      const isOcean = carrierType === 'Ocean';
      const isAir = carrierType === 'Air';

      // Same country? Always try road/air directions (not ocean)
      const sameCountry = originCountry.toUpperCase() === destCountry.toUpperCase();

      let route = [], routeType = '';

      if (isRoad || sameCountry) {
        // Try OSRM for real driving route
        try {
          const r = await fetch(`http://router.project-osrm.org/route/v1/driving/${start[1]},${start[0]};${end[1]},${end[0]}?overview=full&geometries=geojson`);
          const d = await r.json();
          if (d?.routes?.[0]) {
            route = d.routes[0].geometry.coordinates.map(c => [c[1], c[0]]);
            routeType = 'road';
          }
        } catch (e) {}
        // If OSRM fails and it's a cross-border road route, use ocean waypoints
        // But for same-country, show straight line with air curve — roads exist
        if (route.length === 0) {
          if (sameCountry && !isOcean) {
            // Simple great-circle for domestic when OSRM fails
            route = buildRoute(start, [], end, 12);
            routeType = isAir ? 'air' : 'road';
          } else if (!isOcean) {
            const waypoints = getOceanWaypoints(start, end);
            route = buildRoute(start, waypoints, end, 8);
            routeType = 'ocean';
          }
        }
      } else if (isOcean) {
        // Sea lane waypoint routing
        const waypoints = getOceanWaypoints(start, end);
        route = buildRoute(start, waypoints, end, 8);
        routeType = 'ocean';
      } else if (isAir) {
        // Great circle for air (actually correct for flights)
        try {
          // Simple interpolation along great circle
          const pts = [];
          const n = 80;
          const lat1 = start[0] * Math.PI / 180, lon1 = start[1] * Math.PI / 180;
          const lat2 = end[0] * Math.PI / 180, lon2 = end[1] * Math.PI / 180;
          for (let i = 0; i <= n; i++) {
            const f = i / n;
            const d = 2 * Math.asin(Math.sqrt(
              Math.pow(Math.sin((lat2 - lat1) / 2), 2) +
              Math.cos(lat1) * Math.cos(lat2) * Math.pow(Math.sin((lon2 - lon1) / 2), 2)
            ));
            if (d === 0) { pts.push(start); continue; }
            const A = Math.sin((1 - f) * d) / Math.sin(d);
            const B = Math.sin(f * d) / Math.sin(d);
            const x = A * Math.cos(lat1) * Math.cos(lon1) + B * Math.cos(lat2) * Math.cos(lon2);
            const y = A * Math.cos(lat1) * Math.sin(lon1) + B * Math.cos(lat2) * Math.sin(lon2);
            const z = A * Math.sin(lat1) + B * Math.sin(lat2);
            const lat = Math.atan2(z, Math.sqrt(x * x + y * y)) * 180 / Math.PI;
            const lon = Math.atan2(y, x) * 180 / Math.PI;
            pts.push([lat, lon]);
          }
          route = pts;
          routeType = 'air';
        } catch (e) {
          route = [start, end];
          routeType = 'air';
        }
      }

      if (active) setState({ origin: start, dest: end, route, routeType, loading: false, error: null });
    };

    const t = setTimeout(run, 1000);
    return () => { active = false; clearTimeout(t); };
  }, [originCity, originCountry, destCity, destCountry, carrierType]);

  const { origin, dest, route, routeType, loading, error } = state;
  const color = ROUTE_COLORS[carrierType] || '#2563EB';

  const labelMap = {
    road: '🚛 Road Route (OSRM)',
    air: '✈ Great Circle Air Route',
    ocean: '🚢 Sea Lane Route',
  };

  return (
    <div className="map-card">
      <div className="map-card-header">
        <span className="map-card-title">Shipment Route</span>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {routeType && <span className="badge badge-gray">{labelMap[routeType] || routeType}</span>}
          <span className="map-route-label">{originCity} → {destCity}</span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '1rem 1.25rem', background: '#FEF2F2', color: '#DC2626', fontSize: 13 }}>
          ⚠ {error}
        </div>
      )}

      {loading && (
        <div className="map-loading">
          <div className="map-spinner" />
          Calculating route...
        </div>
      )}

      {!loading && !error && (
        <div className="map-wrap">
          <MapContainer center={origin || [20, 0]} zoom={origin ? 3 : 2} style={{ height: '100%', width: '100%' }}>
            {route.length > 0 && <MapUpdater coords={route} />}
            <TileLayer
              attribution='© <a href="https://osm.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {origin && (
              <Marker position={origin}>
                <Popup><b>Origin</b><br />{originCity}, {originCountry}</Popup>
              </Marker>
            )}
            {dest && (
              <Marker position={dest}>
                <Popup><b>Destination</b><br />{destCity}, {destCountry}</Popup>
              </Marker>
            )}
            {route.length > 0 && (
              <Polyline
                positions={route}
                color={color}
                weight={routeType === 'road' ? 3 : 2.5}
                dashArray={routeType === 'road' ? '' : routeType === 'air' ? '6,5' : ''}
                opacity={0.85}
              />
            )}
          </MapContainer>
        </div>
      )}
    </div>
  );
}
