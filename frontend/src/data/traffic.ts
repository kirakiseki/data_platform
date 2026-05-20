export const platformStats = {
  totalTrips: 1194166,
  gpsPoints: 50729499,
  matchedRoads: 47169161,
  routes: 1194166,
  roadSegments: 22304,
  osmNodes: 226042,
  poiCount: 244,
  vehicles: 1386,
}

export const availableDates = ['2015-01-03', '2015-01-04', '2015-01-05', '2015-01-06', '2015-01-07', '2015-01-08']

export const dailyStats = [
  { date: '2015-01-03', trips: 231864, gpsPoints: 9852204, matchedRoads: 9164521, routes: 231864, activeVehicles: 1312, avgSpeed: 34.8 },
  { date: '2015-01-04', trips: 224390, gpsPoints: 9416786, matchedRoads: 8772108, routes: 224390, activeVehicles: 1294, avgSpeed: 35.6 },
  { date: '2015-01-05', trips: 246918, gpsPoints: 10433812, matchedRoads: 9708821, routes: 246918, activeVehicles: 1368, avgSpeed: 34.2 },
  { date: '2015-01-06', trips: 249204, gpsPoints: 10601275, matchedRoads: 9863812, routes: 249204, activeVehicles: 1374, avgSpeed: 33.9 },
  { date: '2015-01-07', trips: 241790, gpsPoints: 10425422, matchedRoads: 9669899, routes: 241790, activeVehicles: 1358, avgSpeed: 34.5 },
  { date: '2015-01-08', trips: 238642, gpsPoints: 10291324, matchedRoads: 9548026, routes: 238642, activeVehicles: 1347, avgSpeed: 34.9 },
]

export const roadClassMeta: Record<string, { label: string, color: string }> = {
  104: { label: '一般道路', color: '#38bdf8' },
  106: { label: '快速通道', color: '#ef4444' },
  108: { label: '居住区道路', color: '#22c55e' },
  110: { label: '城市支路', color: '#64748b' },
  112: { label: '次干路', color: '#f59e0b' },
  114: { label: '主干路', color: '#f97316' },
}

export const roadClassDistribution = [
  { classId: 108, name: '居住区道路', count: 4382 },
  { classId: 114, name: '主干路', count: 4068 },
  { classId: 110, name: '城市支路', count: 3771 },
  { classId: 112, name: '次干路', count: 2819 },
  { classId: 104, name: '一般道路', count: 2659 },
  { classId: 106, name: '快速通道', count: 2432 },
]

export const networkData = [
  { date: '2015-01-05', hour: 0, totalRoads: 22304, smoothRoads: 18234, slowRoads: 2987, congestedRoads: 1083, smoothPct: 81.8, slowPct: 13.4, congestedPct: 4.8, networkAvgSpeed: 42.5 },
  { date: '2015-01-05', hour: 1, totalRoads: 22304, smoothRoads: 18567, slowRoads: 2654, congestedRoads: 1083, smoothPct: 83.2, slowPct: 11.9, congestedPct: 4.9, networkAvgSpeed: 43.8 },
  { date: '2015-01-05', hour: 2, totalRoads: 22304, smoothRoads: 18789, slowRoads: 2456, congestedRoads: 1059, smoothPct: 84.2, slowPct: 11.0, congestedPct: 4.8, networkAvgSpeed: 44.2 },
  { date: '2015-01-05', hour: 3, totalRoads: 22304, smoothRoads: 18654, slowRoads: 2567, congestedRoads: 1083, smoothPct: 83.6, slowPct: 11.5, congestedPct: 4.9, networkAvgSpeed: 43.9 },
  { date: '2015-01-05', hour: 4, totalRoads: 22304, smoothRoads: 18234, slowRoads: 2876, congestedRoads: 1194, smoothPct: 81.7, slowPct: 12.9, congestedPct: 5.4, networkAvgSpeed: 42.3 },
  { date: '2015-01-05', hour: 5, totalRoads: 22304, smoothRoads: 17456, slowRoads: 3234, congestedRoads: 1614, smoothPct: 78.3, slowPct: 14.5, congestedPct: 7.2, networkAvgSpeed: 39.8 },
  { date: '2015-01-05', hour: 6, totalRoads: 22304, smoothRoads: 16234, slowRoads: 3876, congestedRoads: 2194, smoothPct: 72.8, slowPct: 17.4, congestedPct: 9.8, networkAvgSpeed: 36.5 },
  { date: '2015-01-05', hour: 7, totalRoads: 22304, smoothRoads: 14567, slowRoads: 4876, congestedRoads: 2861, smoothPct: 65.3, slowPct: 21.9, congestedPct: 12.8, networkAvgSpeed: 33.2 },
  { date: '2015-01-05', hour: 8, totalRoads: 22304, smoothRoads: 13234, slowRoads: 5234, congestedRoads: 3836, smoothPct: 59.3, slowPct: 23.5, congestedPct: 17.2, networkAvgSpeed: 29.8 },
  { date: '2015-01-05', hour: 9, totalRoads: 22304, smoothRoads: 14876, slowRoads: 4567, congestedRoads: 2861, smoothPct: 66.7, slowPct: 20.5, congestedPct: 12.8, networkAvgSpeed: 34.5 },
  { date: '2015-01-05', hour: 10, totalRoads: 22304, smoothRoads: 15678, slowRoads: 4234, congestedRoads: 2392, smoothPct: 70.3, slowPct: 19.0, congestedPct: 10.7, networkAvgSpeed: 36.8 },
  { date: '2015-01-05', hour: 11, totalRoads: 22304, smoothRoads: 15987, slowRoads: 4012, congestedRoads: 2305, smoothPct: 71.7, slowPct: 18.0, congestedPct: 10.3, networkAvgSpeed: 37.2 },
  { date: '2015-01-05', hour: 12, totalRoads: 22304, smoothRoads: 15456, slowRoads: 4345, congestedRoads: 2503, smoothPct: 69.3, slowPct: 19.5, congestedPct: 11.2, networkAvgSpeed: 35.6 },
  { date: '2015-01-05', hour: 13, totalRoads: 22304, smoothRoads: 15234, slowRoads: 4456, congestedRoads: 2614, smoothPct: 68.3, slowPct: 20.0, congestedPct: 11.7, networkAvgSpeed: 35.1 },
  { date: '2015-01-05', hour: 14, totalRoads: 22304, smoothRoads: 15567, slowRoads: 4234, congestedRoads: 2503, smoothPct: 69.8, slowPct: 19.0, congestedPct: 11.2, networkAvgSpeed: 36.2 },
  { date: '2015-01-05', hour: 15, totalRoads: 22304, smoothRoads: 15123, slowRoads: 4567, congestedRoads: 2614, smoothPct: 67.8, slowPct: 20.5, congestedPct: 11.7, networkAvgSpeed: 34.8 },
  { date: '2015-01-05', hour: 16, totalRoads: 22304, smoothRoads: 14234, slowRoads: 4987, congestedRoads: 3083, smoothPct: 63.8, slowPct: 22.4, congestedPct: 13.8, networkAvgSpeed: 32.5 },
  { date: '2015-01-05', hour: 17, totalRoads: 22304, smoothRoads: 12876, slowRoads: 5456, congestedRoads: 3972, smoothPct: 57.7, slowPct: 24.5, congestedPct: 17.8, networkAvgSpeed: 28.6 },
  { date: '2015-01-05', hour: 18, totalRoads: 22304, smoothRoads: 12234, slowRoads: 5678, congestedRoads: 4392, smoothPct: 54.8, slowPct: 25.5, congestedPct: 19.7, networkAvgSpeed: 27.2 },
  { date: '2015-01-05', hour: 19, totalRoads: 22304, smoothRoads: 13456, slowRoads: 5234, congestedRoads: 3614, smoothPct: 60.3, slowPct: 23.5, congestedPct: 16.2, networkAvgSpeed: 31.5 },
  { date: '2015-01-05', hour: 20, totalRoads: 22304, smoothRoads: 14567, slowRoads: 4876, congestedRoads: 2861, smoothPct: 65.3, slowPct: 21.9, congestedPct: 12.8, networkAvgSpeed: 34.2 },
  { date: '2015-01-05', hour: 21, totalRoads: 22304, smoothRoads: 15678, slowRoads: 4345, congestedRoads: 2281, smoothPct: 70.3, slowPct: 19.5, congestedPct: 10.2, networkAvgSpeed: 37.5 },
  { date: '2015-01-05', hour: 22, totalRoads: 22304, smoothRoads: 16789, slowRoads: 3876, congestedRoads: 1639, smoothPct: 75.3, slowPct: 17.4, congestedPct: 7.3, networkAvgSpeed: 40.2 },
  { date: '2015-01-05', hour: 23, totalRoads: 22304, smoothRoads: 17456, slowRoads: 3456, congestedRoads: 1392, smoothPct: 78.3, slowPct: 15.5, congestedPct: 6.2, networkAvgSpeed: 41.8 },
]

export const hourlyStats = Array.from({ length: 24 }, (_, hour) => {
  const base = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 19 ? 13400 : hour <= 5 ? 5200 : 9200
  return {
    hour,
    trips: Math.round(base + Math.sin(hour / 2) * 1200),
    gpsPoints: Math.round((base + Math.cos(hour / 2) * 900) * 42),
    matchedRoads: Math.round((base + Math.sin(hour / 3) * 850) * 39),
    routes: Math.round(base + Math.sin(hour / 2) * 1200),
    activeVehicles: Math.round((hour <= 5 ? 680 : 1120) + Math.sin(hour / 3) * 120),
    avgSpeed: Number(networkData[hour].networkAvgSpeed.toFixed(1)),
  }
})

export const roadStatusList = [
  { roadId: 1001, roadName: '红军街', roadClass: '主干路', currentSpeed: 15.2, currentFlow: 856, congestionIdx: 4.12, status: '严重拥堵', district: '南岗区' },
  { roadId: 1002, roadName: '中山路', roadClass: '主干路', currentSpeed: 18.6, currentFlow: 723, congestionIdx: 2.87, status: '中度拥堵', district: '香坊区' },
  { roadId: 1003, roadName: '中央大街', roadClass: '居住区道路', currentSpeed: 20.3, currentFlow: 654, congestionIdx: 2.63, status: '中度拥堵', district: '道里区' },
  { roadId: 1004, roadName: '文昌街', roadClass: '主干路', currentSpeed: 21.5, currentFlow: 589, congestionIdx: 2.34, status: '轻度拥堵', district: '南岗区' },
  { roadId: 1005, roadName: '学府路', roadClass: '主干路', currentSpeed: 23.1, currentFlow: 512, congestionIdx: 2.11, status: '轻度拥堵', district: '南岗区' },
  { roadId: 1006, roadName: '友谊路', roadClass: '快速通道', currentSpeed: 28.5, currentFlow: 445, congestionIdx: 1.78, status: '基本畅通', district: '道里区' },
  { roadId: 1007, roadName: '长江路', roadClass: '主干路', currentSpeed: 32.4, currentFlow: 398, congestionIdx: 1.52, status: '基本畅通', district: '开发区' },
  { roadId: 1008, roadName: '和平路', roadClass: '次干路', currentSpeed: 38.6, currentFlow: 367, congestionIdx: 1.24, status: '畅通', district: '香坊区' },
  { roadId: 1009, roadName: '三大动力路', roadClass: '主干路', currentSpeed: 42.3, currentFlow: 334, congestionIdx: 1.05, status: '畅通', district: '香坊区' },
  { roadId: 1010, roadName: '顾乡大街', roadClass: '居住区道路', currentSpeed: 48.7, currentFlow: 289, congestionIdx: 0.87, status: '畅通', district: '道里区' },
]

export const hotspots = {
  district: [
    { zoneId: '230103', zoneName: '南岗区', zoneType: 'district', tripCount: 245678, pickupCount: 123456, dropoffCount: 122222, avgTripDistance: 8.5, avgDuration: 1850, vehicleCount: 12345 },
    { zoneId: '230102', zoneName: '道里区', zoneType: 'district', tripCount: 198765, pickupCount: 98765, dropoffCount: 100000, avgTripDistance: 7.8, avgDuration: 1680, vehicleCount: 10234 },
    { zoneId: '230104', zoneName: '香坊区', zoneType: 'district', tripCount: 167890, pickupCount: 84567, dropoffCount: 83323, avgTripDistance: 9.2, avgDuration: 1920, vehicleCount: 8765 },
    { zoneId: '230109', zoneName: '开发区', zoneType: 'district', tripCount: 134567, pickupCount: 67890, dropoffCount: 66677, avgTripDistance: 10.5, avgDuration: 2100, vehicleCount: 7654 },
    { zoneId: '230111', zoneName: '松北区', zoneType: 'district', tripCount: 89012, pickupCount: 45678, dropoffCount: 43334, avgTripDistance: 12.3, avgDuration: 2450, vehicleCount: 5432 },
  ],
  grid: [
    { zoneId: 'G001', zoneName: '中央大街网格', zoneType: 'grid', tripCount: 45678, pickupCount: 23456, dropoffCount: 22222, avgTripDistance: 5.2, avgDuration: 1250, vehicleCount: 4567 },
    { zoneId: 'G002', zoneName: '哈尔滨站网格', zoneType: 'grid', tripCount: 43210, pickupCount: 22345, dropoffCount: 20865, avgTripDistance: 6.8, avgDuration: 1480, vehicleCount: 4321 },
    { zoneId: 'G003', zoneName: '哈西站网格', zoneType: 'grid', tripCount: 38765, pickupCount: 20123, dropoffCount: 18642, avgTripDistance: 7.5, avgDuration: 1620, vehicleCount: 3876 },
    { zoneId: 'G004', zoneName: '师大网格', zoneType: 'grid', tripCount: 32109, pickupCount: 16789, dropoffCount: 15320, avgTripDistance: 4.8, avgDuration: 1150, vehicleCount: 3210 },
    { zoneId: 'G005', zoneName: '群力网格', zoneType: 'grid', tripCount: 28765, pickupCount: 15234, dropoffCount: 13531, avgTripDistance: 8.2, avgDuration: 1780, vehicleCount: 2876 },
  ],
  poi: [
    { zoneId: 'P001', zoneName: '哈尔滨站', zoneType: 'poi', tripCount: 35678, pickupCount: 15234, dropoffCount: 20444, avgTripDistance: 12.5, avgDuration: 2350, vehicleCount: 5678 },
    { zoneId: 'P002', zoneName: '哈西站', zoneType: 'poi', tripCount: 32109, pickupCount: 16789, dropoffCount: 15320, avgTripDistance: 14.2, avgDuration: 2680, vehicleCount: 5234 },
    { zoneId: 'P003', zoneName: '中央大街商圈', zoneType: 'poi', tripCount: 28765, pickupCount: 14567, dropoffCount: 14198, avgTripDistance: 6.8, avgDuration: 1520, vehicleCount: 4567 },
    { zoneId: 'P004', zoneName: '医大一院', zoneType: 'poi', tripCount: 23456, pickupCount: 11234, dropoffCount: 12222, avgTripDistance: 8.5, avgDuration: 1850, vehicleCount: 3456 },
    { zoneId: 'P005', zoneName: '哈工大', zoneType: 'poi', tripCount: 19876, pickupCount: 9876, dropoffCount: 10000, avgTripDistance: 7.2, avgDuration: 1650, vehicleCount: 2987 },
  ],
}

export const hotspotClusters = [
  { clusterId: 1, centerLon: 126.63, centerLat: 45.76, tripCount: 45678, pickupCount: 23456, dropoffCount: 22222, avgDuration: 1850, clusterType: '商圈型' },
  { clusterId: 2, centerLon: 126.62, centerLat: 45.75, tripCount: 38765, pickupCount: 19876, dropoffCount: 18889, avgDuration: 2100, clusterType: '交通枢纽型' },
  { clusterId: 3, centerLon: 126.65, centerLat: 45.77, tripCount: 32109, pickupCount: 16789, dropoffCount: 15320, avgDuration: 1680, clusterType: '居住型' },
  { clusterId: 4, centerLon: 126.60, centerLat: 45.74, tripCount: 28765, pickupCount: 14567, dropoffCount: 14198, avgDuration: 2350, clusterType: '办公型' },
  { clusterId: 5, centerLon: 126.68, centerLat: 45.78, tripCount: 23456, pickupCount: 12345, dropoffCount: 11111, avgDuration: 1950, clusterType: '混合功能型' },
]

export const distanceHourly = Array.from({ length: 24 }, (_, hour) => {
  const rush = hour >= 7 && hour <= 9 || hour >= 17 && hour <= 19
  return {
    hour,
    shortTrips: Math.round((rush ? 9200 : 4600) + Math.sin(hour / 2) * 900),
    mediumTrips: Math.round((rush ? 13200 : 7200) + Math.cos(hour / 3) * 1200),
    longTrips: Math.round((rush ? 4200 : 2100) + Math.sin(hour / 4) * 420),
    avgDistance: Number((rush ? 8.6 + Math.sin(hour) * 0.8 : 7.1 + Math.cos(hour) * 0.7).toFixed(1)),
  }
})

export const speedHourly = networkData.map(item => ({
  hour: item.hour,
  avgSpeed: item.networkAvgSpeed,
  speedP50: Number((item.networkAvgSpeed * 0.92).toFixed(1)),
  speedP85: Number((item.networkAvgSpeed * 1.22).toFixed(1)),
  speedP95: Number((item.networkAvgSpeed * 1.45).toFixed(1)),
  overspeedRatio: Number((Math.max(0.02, (item.networkAvgSpeed - 32) / 120)).toFixed(3)),
}))

export const timeSlotDaily = [
  { date: '2015-01-03', morningRush: 61234, daytime: 287456, eveningRush: 78421, night: 102345 },
  { date: '2015-01-04', morningRush: 58670, daytime: 265334, eveningRush: 74213, night: 98456 },
  { date: '2015-01-05', morningRush: 69234, daytime: 298345, eveningRush: 86120, night: 108977 },
  { date: '2015-01-06', morningRush: 70456, daytime: 301234, eveningRush: 87452, night: 110324 },
  { date: '2015-01-07', morningRush: 68123, daytime: 292876, eveningRush: 84113, night: 106780 },
  { date: '2015-01-08', morningRush: 66892, daytime: 289450, eveningRush: 82674, night: 104918 },
]

export const odPairs = [
  { rank: 1, from: '南岗区', to: '道里区', trips: 35876, avgDistance: 8.1, mainPurpose: '通勤/商圈' },
  { rank: 2, from: '哈尔滨站', to: '中央大街商圈', trips: 29765, avgDistance: 4.7, mainPurpose: '交通接驳' },
  { rank: 3, from: '哈西站', to: '南岗区', trips: 25433, avgDistance: 9.5, mainPurpose: '枢纽换乘' },
  { rank: 4, from: '香坊区', to: '开发区', trips: 21178, avgDistance: 11.8, mainPurpose: '跨区通勤' },
  { rank: 5, from: '道里区', to: '群力新区', trips: 18654, avgDistance: 7.2, mainPurpose: '居住出行' },
]

export function formatNumber(value: number) {
  return value.toLocaleString('zh-CN')
}

export function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  if (status === '畅通' || status === '基本畅通') return 'success'
  if (status === '轻度拥堵') return 'warning'
  if (status === '中度拥堵' || status === '严重拥堵') return 'danger'
  return 'info'
}

export function statusColor(status: string): string {
  if (status === '严重拥堵') return '#FF0000'
  if (status === '中度拥堵') return '#FF9900'
  if (status === '轻度拥堵') return '#FFFF00'
  if (status === '基本畅通') return '#99CC00'
  return '#008000'
}

export function speedTone(speed: number) {
  if (speed >= 38) return 'success'
  if (speed >= 30) return 'warning'
  return 'danger'
}
