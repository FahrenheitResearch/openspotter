import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createReport } from '../services/api'
import clsx from 'clsx'

const reportTypes = [
  { value: 'tornado', label: 'Tornado', color: 'bg-red-600' },
  { value: 'funnel_cloud', label: 'Funnel Cloud', color: 'bg-orange-500' },
  { value: 'wall_cloud', label: 'Wall Cloud', color: 'bg-yellow-500' },
  { value: 'rotation', label: 'Rotation', color: 'bg-amber-500' },
  { value: 'hail', label: 'Hail', color: 'bg-purple-600' },
  { value: 'wind_damage', label: 'Wind Damage', color: 'bg-cyan-600' },
  { value: 'flooding', label: 'Flooding', color: 'bg-blue-600' },
  { value: 'flash_flood', label: 'Flash Flood', color: 'bg-blue-800' },
  { value: 'heavy_rain', label: 'Heavy Rain', color: 'bg-blue-400' },
  { value: 'wildfire', label: 'Wildfire', color: 'bg-orange-600' },
  { value: 'other', label: 'Other', color: 'bg-gray-600' },
]

interface ReportFormProps {
  latitude?: number
  longitude?: number
  onSuccess?: () => void
  onCancel?: () => void
}

export default function ReportForm({
  latitude,
  longitude,
  onSuccess,
  onCancel,
}: ReportFormProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    type: '',
    description: '',
    severity: 3,
    hail_size: '',
    wind_speed: '',
    latitude: latitude || 0,
    longitude: longitude || 0,
  })
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: createReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      onSuccess?.()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to submit report')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!formData.type) {
      setError('Please select a report type')
      return
    }

    if (!formData.latitude || !formData.longitude) {
      setError('Please select a location on the map')
      return
    }

    mutation.mutate({
      type: formData.type,
      description: formData.description || undefined,
      severity: formData.severity,
      latitude: formData.latitude,
      longitude: formData.longitude,
      hail_size: formData.hail_size ? parseFloat(formData.hail_size) : undefined,
      wind_speed: formData.wind_speed ? parseInt(formData.wind_speed) : undefined,
    })
  }

  // Get user's current location
  const getCurrentLocation = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setFormData((prev) => ({
            ...prev,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }))
        },
        (err) => {
          setError('Could not get your location: ' + err.message)
        },
        { enableHighAccuracy: true }
      )
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-bold">Submit Weather Report</h3>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Report Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Report Type *
        </label>
        <div className="grid grid-cols-3 gap-2">
          {reportTypes.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => setFormData((prev) => ({ ...prev, type: type.value }))}
              className={clsx(
                'p-2 rounded-md text-sm font-medium transition-all',
                formData.type === type.value
                  ? `${type.color} text-white ring-2 ring-offset-2 ring-gray-500`
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Location */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Location *
        </label>
        <div className="flex space-x-2">
          <input
            type="number"
            step="any"
            placeholder="Latitude"
            value={formData.latitude || ''}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                latitude: parseFloat(e.target.value),
              }))
            }
            className="flex-1 px-3 py-2 border rounded-md text-sm"
          />
          <input
            type="number"
            step="any"
            placeholder="Longitude"
            value={formData.longitude || ''}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                longitude: parseFloat(e.target.value),
              }))
            }
            className="flex-1 px-3 py-2 border rounded-md text-sm"
          />
          <button
            type="button"
            onClick={getCurrentLocation}
            className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm"
            title="Use current location"
          >
            GPS
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Click on the map or use GPS to set location
        </p>
      </div>

      {/* Severity */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Severity: {formData.severity}/5
        </label>
        <input
          type="range"
          min="1"
          max="5"
          value={formData.severity}
          onChange={(e) =>
            setFormData((prev) => ({
              ...prev,
              severity: parseInt(e.target.value),
            }))
          }
          className="w-full"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>Minor</span>
          <span>Moderate</span>
          <span>Significant</span>
          <span>Severe</span>
          <span>Extreme</span>
        </div>
      </div>

      {/* Type-specific fields */}
      {formData.type === 'hail' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Hail Size (inches)
          </label>
          <input
            type="number"
            step="0.25"
            min="0"
            max="10"
            placeholder="e.g., 1.75"
            value={formData.hail_size}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, hail_size: e.target.value }))
            }
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
      )}

      {formData.type === 'wind_damage' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Estimated Wind Speed (mph)
          </label>
          <input
            type="number"
            min="0"
            max="350"
            placeholder="e.g., 75"
            value={formData.wind_speed}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, wind_speed: e.target.value }))
            }
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
      )}

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description
        </label>
        <textarea
          placeholder="Describe what you observed..."
          value={formData.description}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, description: e.target.value }))
          }
          rows={3}
          className="w-full px-3 py-2 border rounded-md"
        />
      </div>

      {/* Actions */}
      <div className="flex space-x-3 pt-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex-1 bg-primary-600 hover:bg-primary-700 text-white py-2 px-4 rounded-md font-medium disabled:opacity-50"
        >
          {mutation.isPending ? 'Submitting...' : 'Submit Report'}
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
