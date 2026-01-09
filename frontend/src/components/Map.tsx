import { useEffect, useRef, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { fetchActiveSpotters, fetchReports } from '../services/api'
import { wsService } from '../services/websocket'
import { useAuthStore } from '../store/auth'

// Report type icons
const reportIcons: Record<string, string> = {
  tornado: 'T',
  funnel_cloud: 'F',
  wall_cloud: 'W',
  hail: 'H',
  wind_damage: 'WD',
  flooding: 'FL',
  flash_flood: 'FF',
  wildfire: 'FI',
  other: '?',
}

// Create custom marker icons
function createSpotterIcon(role: string): L.DivIcon {
  const roleColors: Record<string, string> = {
    spotter: '#3b82f6',
    verified_spotter: '#10b981',
    coordinator: '#8b5cf6',
    admin: '#ef4444',
  }

  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="spotter-marker ${role}" style="background-color: ${roleColors[role] || '#6b7280'}"></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  })
}

function createReportIcon(type: string, verified: boolean): L.DivIcon {
  const typeColors: Record<string, string> = {
    tornado: '#dc2626',
    funnel_cloud: '#f97316',
    wall_cloud: '#eab308',
    hail: '#7c3aed',
    wind_damage: '#0891b2',
    flooding: '#2563eb',
    flash_flood: '#1d4ed8',
    wildfire: '#ea580c',
    other: '#6b7280',
  }

  const color = typeColors[type] || '#6b7280'
  const icon = reportIcons[type] || '?'
  const border = verified ? '3px solid #10b981' : '2px solid white'

  return L.divIcon({
    className: 'custom-marker',
    html: `<div class="report-marker" style="background-color: ${color}; border: ${border}; font-size: 10px; color: white; font-weight: bold;">${icon}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  })
}

interface SpotterFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    user_id?: string
    callsign?: string
    role?: string
    heading?: number
    speed?: number
    timestamp: string
  }
}

interface ReportFeature {
  type: 'Feature'
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    id: string
    type: string
    title?: string
    description?: string
    severity?: number
    is_verified: boolean
    reporter_callsign?: string
    created_at: string
  }
}

function LocationUpdater({
  onUpdate,
}: {
  onUpdate: (spotters: SpotterFeature[]) => void
}) {
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (!isAuthenticated) return

    wsService.connectLocation()

    const cleanup = wsService.onLocationUpdate((data) => {
      // Update spotter position in real-time
      onUpdate((prev: SpotterFeature[]) => {
        const existing = prev.findIndex(
          (s) => s.properties.user_id === data.user_id
        )
        const newFeature: SpotterFeature = {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [data.longitude, data.latitude],
          },
          properties: {
            user_id: data.user_id,
            callsign: data.callsign,
            role: data.role,
            heading: data.heading,
            speed: data.speed,
            timestamp: data.timestamp,
          },
        }

        if (existing >= 0) {
          const updated = [...prev]
          updated[existing] = newFeature
          return updated
        }
        return [...prev, newFeature]
      })
    })

    return () => {
      cleanup()
      wsService.disconnectLocation()
    }
  }, [isAuthenticated, onUpdate])

  return null
}

function MapController({ center }: { center?: [number, number] }) {
  const map = useMap()

  useEffect(() => {
    if (center) {
      map.setView(center, map.getZoom())
    }
  }, [center, map])

  return null
}

interface MapProps {
  showSpotters?: boolean
  showReports?: boolean
  reportType?: string
  reportHours?: number
  onMapClick?: (lat: number, lng: number) => void
}

export default function Map({
  showSpotters = true,
  showReports = true,
  reportType,
  reportHours = 24,
  onMapClick,
}: MapProps) {
  const [spotters, setSpotters] = useState<SpotterFeature[]>([])
  const [userLocation, setUserLocation] = useState<[number, number] | null>(null)
  const mapRef = useRef<L.Map | null>(null)

  // Fetch active spotters
  const { data: spotterData } = useQuery({
    queryKey: ['spotters'],
    queryFn: fetchActiveSpotters,
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: showSpotters,
  })

  // Fetch reports
  const { data: reportData } = useQuery({
    queryKey: ['reports', reportType, reportHours],
    queryFn: () =>
      fetchReports({
        type: reportType,
        hours: reportHours,
      }),
    refetchInterval: 60000, // Refresh every minute
    enabled: showReports,
  })

  // Update spotters from query
  useEffect(() => {
    if (spotterData?.features) {
      setSpotters(spotterData.features)
    }
  }, [spotterData])

  // Get user's location
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation([position.coords.latitude, position.coords.longitude])
        },
        () => {
          // Default to center of US
          setUserLocation([39.8283, -98.5795])
        }
      )
    }
  }, [])

  const defaultCenter: [number, number] = userLocation || [39.8283, -98.5795]

  return (
    <div className="h-full w-full relative">
      <MapContainer
        center={defaultCenter}
        zoom={6}
        className="h-full w-full"
        ref={mapRef}
        whenReady={(map) => {
          if (onMapClick) {
            map.target.on('click', (e: L.LeafletMouseEvent) => {
              onMapClick(e.latlng.lat, e.latlng.lng)
            })
          }
        }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapController center={userLocation || undefined} />
        <LocationUpdater onUpdate={setSpotters as any} />

        {/* Spotter markers */}
        {showSpotters &&
          spotters.map((spotter) => (
            <Marker
              key={spotter.properties.user_id || spotter.properties.callsign}
              position={[
                spotter.geometry.coordinates[1],
                spotter.geometry.coordinates[0],
              ]}
              icon={createSpotterIcon(spotter.properties.role || 'spotter')}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold">
                    {spotter.properties.callsign || 'Anonymous'}
                  </p>
                  <p className="text-gray-500 capitalize">
                    {spotter.properties.role?.replace('_', ' ')}
                  </p>
                  {spotter.properties.speed && (
                    <p>Speed: {Math.round(spotter.properties.speed * 2.237)} mph</p>
                  )}
                  <p className="text-xs text-gray-400">
                    {new Date(spotter.properties.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

        {/* Report markers */}
        {showReports &&
          reportData?.features?.map((report: ReportFeature) => (
            <Marker
              key={report.properties.id}
              position={[
                report.geometry.coordinates[1],
                report.geometry.coordinates[0],
              ]}
              icon={createReportIcon(
                report.properties.type,
                report.properties.is_verified
              )}
            >
              <Popup>
                <div className="text-sm max-w-xs">
                  <p className="font-bold capitalize">
                    {report.properties.type.replace('_', ' ')}
                    {report.properties.is_verified && (
                      <span className="ml-2 text-green-600">Verified</span>
                    )}
                  </p>
                  {report.properties.title && (
                    <p className="font-medium">{report.properties.title}</p>
                  )}
                  {report.properties.description && (
                    <p className="text-gray-600">{report.properties.description}</p>
                  )}
                  {report.properties.severity && (
                    <p>Severity: {report.properties.severity}/5</p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    Reported by {report.properties.reporter_callsign || 'Anonymous'}
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(report.properties.created_at).toLocaleString()}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-white p-3 rounded-lg shadow-lg z-[1000] text-sm">
        <h4 className="font-bold mb-2">Legend</h4>
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-blue-500"></div>
            <span>Spotter</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-green-500"></div>
            <span>Verified Spotter</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded-full bg-purple-500"></div>
            <span>Coordinator</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded bg-red-600"></div>
            <span>Tornado</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded bg-purple-600"></div>
            <span>Hail</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded bg-blue-600"></div>
            <span>Flooding</span>
          </div>
        </div>
      </div>
    </div>
  )
}
