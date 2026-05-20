import api from './index'

export interface RoadFeature {
  type: 'Feature'
  geometry: any
  properties: {
    gid: number
    osm_id: number
    class_id: number
    length: number
    maxspeed_forward: number | null
    maxspeed_backward: number | null
    priority: number
  }
}

export interface GeoJSONFeatureCollection {
  type: 'FeatureCollection'
  features: RoadFeature[]
  next_cursor?: number | null
}

export interface RoadsBboxOptions {
  classId?: number
  cursor?: number
  simplifyTolerance?: number
  signal?: AbortSignal
}

export interface RoadStats {
  total_roads: number
  by_class: Record<string, number>
}

export interface POI {
  name: string
  type: string
  lon: number
  lat: number
}

export interface Hotspot {
  name: string
  lon: number
  lat: number
  trip_count: number
}

export interface MapRoadFeature {
  gid: number
  osm_id: number
  class_id: number
  length: number
  maxspeed_forward: number | null
  maxspeed_backward: number | null
  priority: number
  geom_json: any
}

export interface MapData {
  roads: MapRoadFeature[]
}

export function getRoadsByBbox(
  minLng: number,
  minLat: number,
  maxLng: number,
  maxLat: number,
  limit = 2000,
  options: RoadsBboxOptions = {},
) {
  const params: any = { min_lng: minLng, min_lat: minLat, max_lng: maxLng, max_lat: maxLat, limit }
  if (options.classId !== undefined) {
    params.class_id = options.classId
  }
  if (options.cursor !== undefined && options.cursor !== null) {
    params.cursor = options.cursor
  }
  if (options.simplifyTolerance !== undefined && options.simplifyTolerance > 0) {
    params.simplify_tolerance = options.simplifyTolerance
  }
  return api.get<any, GeoJSONFeatureCollection>('/roads/bbox/geojson', {
    params,
    signal: options.signal,
  })
}

export function getRoadStats() {
  return api.get<any, RoadStats>('/roads/stats')
}

export function getMapData() {
  return api.get<any, MapData>('/map/data')
}
