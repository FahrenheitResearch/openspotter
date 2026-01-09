import { useEffect, useRef, useState, useCallback } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap, GeoJSON, LayersControl } from 'react-leaflet'
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

// Fetch WFO boundaries from NWS MapServer
async function fetchWFOBoundaries() {
  const url = 'https://mapservices.weather.noaa.gov/static/rest/services/nws_reference_maps/nws_reference_map/MapServer/1/query?where=1%3D1&outFields=CWA,WFO,City,State&returnGeometry=true&outSR=4326&f=geojson'

  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('Failed to fetch WFO boundaries')
  }
  return response.json()
}

// WFO boundary styling
function wfoStyle() {
  return {
    color: '#ff6b35',
    weight: 2,
    opacity: 0.8,
    fillColor: '#ff6b35',
    fillOpacity: 0.05,
  }
}

// WFO popup content
function onEachWFO(feature: any, layer: L.Layer) {
  if (feature.properties) {
    const { CWA, WFO, City, State } = feature.properties
    layer.bindPopup(`
      <div class="text-sm">
        <p class="font-bold text-orange-600">${CWA || WFO}</p>
        <p>${City || 'Unknown'}, ${State || ''}</p>
        <p class="text-xs text-gray-500">Weather Forecast Office</p>
      </div>
    `)
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
  const [showWFO, setShowWFO] = useState(false)
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

  // Fetch WFO boundaries (only when enabled)
  const { data: wfoData } = useQuery({
    queryKey: ['wfo-boundaries'],
    queryFn: fetchWFOBoundaries,
    enabled: showWFO,
    staleTime: 1000 * 60 * 60 * 24, // Cache for 24 hours
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

  const onEachWFOFeature = useCallback((feature: any, layer: L.Layer) => {
    onEachWFO(feature, layer)
  }, [])

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
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="OpenStreetMap">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="Satellite">
            <TileLayer
              attribution='&copy; Esri'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>

          <LayersControl.Overlay name="WFO Boundaries">
            <GeoJSON
              key={showWFO ? 'wfo-loaded' : 'wfo-empty'}
              data={wfoData || { type: 'FeatureCollection', features: [] }}
              style={wfoStyle}
              onEachFeature={onEachWFOFeature}
            />
          </LayersControl.Overlay>
        </LayersControl>

        <MapController center={userLocation || undefined} />
        <LocationUpdater onUpdate={setSpotters as any} />

        {/* WFO Layer (when data loaded via overlay) */}
        {showWFO && wfoData && (
          <GeoJSON
            key="wfo-boundaries"
            data={wfoData}
            style={wfoStyle}
            onEachFeature={onEachWFOFeature}
          />
        )}

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

      {/* Layer toggle panel */}
      <div className="absolute top-4 left-4 bg-white p-3 rounded-lg shadow-lg z-[1000] text-sm">
        <h4 className="font-bold mb-2">Layers</h4>
        <label className="flex items-center space-x-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showWFO}
            onChange={(e) => setShowWFO(e.target.checked)}
            className="rounded border-gray-300 text-orange-500 focus:ring-orange-500"
          />
          <span className="flex items-center">
            <span className="w-3 h-3 border-2 border-orange-500 mr-2"></span>
            WFO Boundaries
          </span>
        </label>
      </div>

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
          {showWFO && (
            <div className="flex items-center space-x-2 pt-1 border-t">
              <div className="w-4 h-4 border-2 border-orange-500 bg-orange-500/10"></div>
              <span>WFO Area</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
