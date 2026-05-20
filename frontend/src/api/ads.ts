import api from './index'

export interface AdsNetworkStatusHourlyMetric {
  stat_date: string
  hour: number
  total_roads: number
  smooth_roads: number
  basically_smooth_roads: number
  light_congested_roads: number
  moderate_congested_roads: number
  severe_congested_roads: number
  smooth_pct: number
  basically_smooth_pct: number
  light_congested_pct: number
  moderate_congested_pct: number
  severe_congested_pct: number
  network_avg_speed: number | null
}

export interface AdsCongestionHourlyMetric {
  stat_date: string
  hour: number
  light_congested_roads: number
  moderate_congested_roads: number
  severe_congested_roads: number
  avg_congestion: number | null
  total_delay_min: number | null
}

export interface AdsTopCongestedRoadMetric {
  rank_id: number
  stat_date: string
  hour: number
  road_id: number
  road_name: string | null
  congestion_idx: number | null
  avg_speed: number | null
  trip_count: number | null
  duration_loss: number | null
}

export interface AdsTripDistanceHourlyMetric {
  stat_date: string
  hour: number
  short_trips: number
  medium_trips: number
  long_trips: number
  avg_distance: number | null
  total_distance: number | null
  sample_count: number | null
}

export interface AdsTripSpeedHourlyMetric {
  stat_date: string
  hour: number
  avg_speed: number | null
  speed_p50: number | null
  speed_p85: number | null
  speed_p95: number | null
  overspeed_ratio: number | null
  sample_count: number | null
}

export interface AdsTripTimeslotDailyMetric {
  stat_date: string
  morning_rush: number
  daytime: number
  evening_rush: number
  night: number
  weekday_trips: number | null
  holiday_trips: number | null
  sample_count: number | null
}

export interface AdsHotspotMonitorDailyMetric {
  stat_date: string
  zone_type: string
  hotspot_count: number
  total_trip_count: number
  total_pickup_count: number
  total_dropoff_count: number
  max_hotspot_zone_id: string | null
  max_hotspot_zone_name: string | null
  max_hotspot_trip_count: number | null
}

interface ItemsResponse<T> {
  items: T[]
}

export function getAdsNetworkStatusHourly(date: string) {
  return api.get<any, ItemsResponse<AdsNetworkStatusHourlyMetric>>('/data/ads/network-status/hourly', {
    params: { date },
  })
}

export function getAdsCongestionHourly(date: string) {
  return api.get<any, ItemsResponse<AdsCongestionHourlyMetric>>('/data/ads/congestion/hourly', {
    params: { date },
  })
}

export function getAdsTopCongestedRoads(date: string, hour: number, limit = 10) {
  return api.get<any, ItemsResponse<AdsTopCongestedRoadMetric>>('/data/ads/top-congested-roads', {
    params: { date, hour, limit },
  })
}

export function getAdsTripDistanceHourly(date: string) {
  return api.get<any, ItemsResponse<AdsTripDistanceHourlyMetric>>('/data/ads/trips/distance/hourly', {
    params: { date },
  })
}

export function getAdsTripSpeedHourly(date: string) {
  return api.get<any, ItemsResponse<AdsTripSpeedHourlyMetric>>('/data/ads/trips/speed/hourly', {
    params: { date },
  })
}

export function getAdsTripTimeslotDaily() {
  return api.get<any, ItemsResponse<AdsTripTimeslotDailyMetric>>('/data/ads/trips/timeslot/daily')
}

export type HotspotMonitorTimeMode = 'all' | 'day' | 'hour'

export function getAdsHotspotMonitorDaily(timeMode: HotspotMonitorTimeMode, date?: string, hour?: number) {
  const params: Record<string, string | number> = { time_mode: timeMode }
  if (date) params.date = date
  if (hour != null) params.hour = hour
  return api.get<any, ItemsResponse<AdsHotspotMonitorDailyMetric>>('/data/ads/hotspots/monitor/daily', {
    params,
  })
}
