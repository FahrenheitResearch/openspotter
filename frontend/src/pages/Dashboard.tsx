import { useState, useEffect } from 'react'
import Map from '../components/Map'
import ReportForm from '../components/ReportForm'
import Chat from '../components/Chat'
import { useAuthStore } from '../store/auth'
import { wsService } from '../services/websocket'
import clsx from 'clsx'

export default function Dashboard() {
  const { isAuthenticated, user } = useAuthStore()
  const [showReportForm, setShowReportForm] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const [reportLocation, setReportLocation] = useState<{
    lat: number
    lng: number
  } | null>(null)
  const [isSharing, setIsSharing] = useState(false)
  const [sharingInterval, setSharingInterval] = useState<number | null>(null)

  // Start/stop location sharing
  const toggleLocationSharing = () => {
    if (isSharing) {
      // Stop sharing
      if (sharingInterval) {
        clearInterval(sharingInterval)
        setSharingInterval(null)
      }
      wsService.stopLocationSharing()
      setIsSharing(false)
    } else {
      // Start sharing
      wsService.connectLocation()

      const updateLocation = () => {
        if ('geolocation' in navigator) {
          navigator.geolocation.getCurrentPosition(
            (position) => {
              wsService.sendLocationUpdate({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                altitude: position.coords.altitude || undefined,
                accuracy: position.coords.accuracy,
                heading: position.coords.heading || undefined,
                speed: position.coords.speed || undefined,
                visibility: user?.share_location_with || 'public',
              })
            },
            (error) => {
              console.error('Location error:', error)
            },
            { enableHighAccuracy: true }
          )
        }
      }

      // Update immediately
      updateLocation()

      // Then update every 10 seconds
      const interval = setInterval(updateLocation, 10000)
      setSharingInterval(interval as unknown as number)
      setIsSharing(true)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (sharingInterval) {
        clearInterval(sharingInterval)
      }
    }
  }, [sharingInterval])

  const handleMapClick = (lat: number, lng: number) => {
    if (isAuthenticated) {
      setReportLocation({ lat, lng })
      setShowReportForm(true)
    }
  }

  return (
    <div className="flex-1 flex flex-col lg:flex-row relative">
      {/* Main map area */}
      <div className="flex-1 relative">
        <Map onMapClick={handleMapClick} />

        {/* Floating controls */}
        <div className="absolute top-4 right-4 z-[1000] flex flex-col space-y-2">
          {isAuthenticated && (
            <>
              {/* Location sharing toggle */}
              <button
                onClick={toggleLocationSharing}
                className={clsx(
                  'px-4 py-2 rounded-lg shadow-lg font-medium text-sm transition-all',
                  isSharing
                    ? 'bg-green-500 hover:bg-green-600 text-white'
                    : 'bg-white hover:bg-gray-50 text-gray-700'
                )}
              >
                {isSharing ? 'Stop Sharing' : 'Share Location'}
              </button>

              {/* New report button */}
              <button
                onClick={() => setShowReportForm(true)}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg shadow-lg font-medium text-sm"
              >
                New Report
              </button>

              {/* Chat toggle */}
              <button
                onClick={() => setShowChat(!showChat)}
                className={clsx(
                  'px-4 py-2 rounded-lg shadow-lg font-medium text-sm transition-all',
                  showChat
                    ? 'bg-primary-600 text-white'
                    : 'bg-white hover:bg-gray-50 text-gray-700'
                )}
              >
                Chat
              </button>
            </>
          )}

          {!isAuthenticated && (
            <div className="bg-white rounded-lg shadow-lg p-4 text-sm">
              <p className="text-gray-600 mb-2">
                Login to share your location and submit reports
              </p>
              <a
                href="/login"
                className="block text-center bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md font-medium"
              >
                Login
              </a>
            </div>
          )}
        </div>

        {/* Status indicator */}
        {isSharing && (
          <div className="absolute bottom-4 right-4 z-[1000] bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2">
            <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
            <span className="text-sm font-medium">Sharing Location</span>
          </div>
        )}
      </div>

      {/* Sidebar panels */}
      {showReportForm && (
        <div className="absolute inset-0 lg:relative lg:inset-auto lg:w-96 z-[1001] bg-white lg:shadow-lg overflow-auto">
          <div className="p-4">
            <ReportForm
              latitude={reportLocation?.lat}
              longitude={reportLocation?.lng}
              onSuccess={() => {
                setShowReportForm(false)
                setReportLocation(null)
              }}
              onCancel={() => {
                setShowReportForm(false)
                setReportLocation(null)
              }}
            />
          </div>
        </div>
      )}

      {showChat && !showReportForm && (
        <div className="absolute inset-0 lg:relative lg:inset-auto lg:w-96 z-[1001] bg-white lg:shadow-lg">
          <div className="h-full flex flex-col">
            <div className="p-2 border-b flex justify-between items-center lg:hidden">
              <h3 className="font-medium">Chat</h3>
              <button
                onClick={() => setShowChat(false)}
                className="p-1 hover:bg-gray-100 rounded"
              >
                Close
              </button>
            </div>
            <div className="flex-1">
              <Chat />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
