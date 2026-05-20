import api from './index'

export interface DashboardPageResponse {
  platform_stats: {
    total_trips: number
    total_vehicles: number
    total_distance_km: number | null
    road_segments: number
    total_pois: number
  }
  day_stats: {
    trips: number
    vehicles: number
    distance_km: number | null
    avg_speed: number | null
    morning_rush_trips: number | null
    evening_rush_trips: number | null
  } | null
  hour_stats: {
    trips: number
    vehicles: number
    avg_speed: number | null
  } | null
  network_trend: Array<{
    hour: number
    avg_speed: number | null
    smooth_pct: number | null
    congested_pct: number | null
  }>
  distance_trend: Array<{
    hour: number
    short_trips: number
    medium_trips: number
    long_trips: number
  }>
  top_roads: Array<{
    rank: number
    road_id: number
    road_name: string | null
    congestion_idx: number | null
    avg_speed: number | null
    status: string | null
  }>
  top_hotspots: Array<{
    zone_id: string
    zone_name: string | null
    zone_type: string
    trip_count: number
    avg_trip_distance: number | null
  }>
}

export interface RoadStatusPageItem {
  road_id: number
  road_name: string | null
  road_class: string | null
  district_code: string | null
  district_name: string | null
  current_speed: number | null
  current_flow: number | null
  congestion_idx: number | null
  status: string | null
}

export interface RoadStatusPageResponse {
  summary: {
    total_roads: number
    congested_roads: number
    severe_congested_roads: number
    avg_speed: number | null
    congestion_pct: number | null
  }
  total: number
  page: number
  page_size: number
  items: RoadStatusPageItem[]
}

export interface GeoJSONFeatureCollection<TProperties = Record<string, unknown>> {
  type: 'FeatureCollection'
  features: Array<{
    type: 'Feature'
    geometry: any
    properties: TProperties
  }>
}

export interface CongestionRoadProperties {
  road_id: number
  road_name: string | null
  status: string | null
  congestion_idx: number | null
  avg_speed: number | null
  trip_count: number | null
}

export interface CongestionRoadRankingItem {
  road_id: number
  road_name: string | null
  status: string | null
  congestion_idx: number | null
  avg_speed: number | null
  trip_count: number | null
}

export interface CongestionRoadRankingResponse {
  items: CongestionRoadRankingItem[]
}

export interface HotspotZoneItem {
  zone_id: string
  zone_name: string | null
  zone_type: string
  center_lon: number | null
  center_lat: number | null
  trip_count: number
  pickup_count: number
  dropoff_count: number
  vehicle_count: number | null
  avg_trip_distance: number | null
  avg_duration: number | null
}

export interface HotspotZoneListResponse {
  total: number
  page: number
  page_size: number
  items: HotspotZoneItem[]
}

export interface TripOdItem {
  rank: number
  origin_name: string | null
  origin_lon: number | null
  origin_lat: number | null
  dest_name: string | null
  dest_lon: number | null
  dest_lat: number | null
  trip_count: number
  avg_distance: number | null
  avg_duration: number | null
  flow_direction: string | null
}

export interface TripOdPageResponse {
  items: TripOdItem[]
}

export interface TrajectoryDailyStatsItem {
  stat_date: string
  trips: number
  total_vehicles: number
  total_gps_points: number | null
  total_matched_roads: number | null
  avg_speed: number | null
}

export interface TrajectorySampleItem {
  trip_id: number
  devid: string
  trip_date: string
  start_hour: number | null
  total_distance_m: number | null
  duration_s: number | null
  route_line: any
  route_source?: 'matched' | 'raw' | null
}

export type TrajectoryRouteSource = 'matched' | 'raw'

export type DashboardTimeMode = 'all' | 'day' | 'hour'

export type HotspotZoneType = 'district' | 'grid' | 'poi' | 'cluster'

export function getPageDashboard(
  timeMode: DashboardTimeMode,
  date?: string,
  hour?: number,
  topN = 5,
  hotspotZoneType: HotspotZoneType = 'poi',
) {
  const params: any = { time_mode: timeMode, top_n: topN, hotspot_zone_type: hotspotZoneType }
  if (date !== undefined) {
    params.date = date
  }
  if (hour !== undefined) {
    params.hour = hour
  }
  return api.get<any, DashboardPageResponse>('/page/dashboard', {
    params,
  })
}

export function getPageRoadStatus(date: string, hour: number, pageSize = 100, status?: string) {
  return api.get<any, RoadStatusPageResponse>('/page/road-status', {
    params: { date, hour, page_size: pageSize, status },
  })
}

export interface CongestionGeojsonOptions {
  status?: string
  allRoads?: boolean
  centerLng?: number
  centerLat?: number
  bbox?: { minLng: number, minLat: number, maxLng: number, maxLat: number }
  cursor?: number
  simplifyTolerance?: number
  signal?: AbortSignal
}

export interface CongestionRoadsGeojsonResponse extends GeoJSONFeatureCollection<CongestionRoadProperties> {
  next_cursor: number | null
}

export function getPageCongestionRoadsGeojson(
  date: string,
  hour: number,
  limit = 2000,
  options: CongestionGeojsonOptions = {},
) {
  const params: any = { date, hour, limit, all_roads: options.allRoads ?? false }
  if (options.status !== undefined) {
    params.status = options.status
  }
  if (options.centerLng !== undefined && options.centerLat !== undefined) {
    params.center_lng = options.centerLng
    params.center_lat = options.centerLat
  }
  if (options.bbox) {
    params.min_lng = options.bbox.minLng
    params.min_lat = options.bbox.minLat
    params.max_lng = options.bbox.maxLng
    params.max_lat = options.bbox.maxLat
  }
  if (options.cursor !== undefined && options.cursor !== null) {
    params.cursor = options.cursor
  }
  if (options.simplifyTolerance !== undefined && options.simplifyTolerance > 0) {
    params.simplify_tolerance = options.simplifyTolerance
  }
  return api.get<any, CongestionRoadsGeojsonResponse>('/page/congestion/roads/geojson', {
    params,
    signal: options.signal,
  })
}

export function getPageCongestionRoadsRanking(
  date: string,
  hour: number,
  sortBy: 'congestion' | 'flow' = 'congestion',
  limit = 20,
) {
  return api.get<any, CongestionRoadRankingResponse>('/page/congestion/roads/ranking', {
    params: { date, hour, sort_by: sortBy, limit },
  })
}

export function getPageHotspotZones(zoneType: string, date: string, hour?: number, pageSize = 200) {
  return api.get<any, HotspotZoneListResponse>('/page/hotspot/zones', {
    params: { zone_type: zoneType, date, hour, page_size: pageSize },
  })
}

export function getPageTripOd(date: string, topN = 10, flowDirection?: string) {
  return api.get<any, TripOdPageResponse>('/page/trip-features/od', {
    params: { date, top_n: topN, flow_direction: flowDirection },
  })
}

export function getPageTrajectoryDailyStats() {
  return api.get<any, { items: TrajectoryDailyStatsItem[] }>('/page/trajectory/daily-stats')
}

export function getPageTrajectorySamples(
  date?: string,
  hour?: number,
  sampleSize = 8,
  routeSource: TrajectoryRouteSource = 'matched',
) {
  return api.get<any, { items: TrajectorySampleItem[] }>('/page/trajectory/samples', {
    params: { date, hour, sample_size: sampleSize, route_source: routeSource },
  })
}
