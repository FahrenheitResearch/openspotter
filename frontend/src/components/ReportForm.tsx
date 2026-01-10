import { useState, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createReport, uploadMedia } from '../services/api'
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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [formData, setFormData] = useState({
    type: '',
    description: '',
    severity: 3,
    hail_size: '',
    wind_speed: '',
    latitude: latitude || 0,
    longitude: longitude || 0,
    post_to_twitter: false,
  })
  const [mediaFiles, setMediaFiles] = useState<File[]>([])
  const [mediaUrls, setMediaUrls] = useState<string[]>([])
  const [mediaPreviews, setMediaPreviews] = useState<string[]>([])
  const [uploadingMedia, setUploadingMedia] = useState(false)
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

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    // Validate files
    const maxSize = 10 * 1024 * 1024 // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/quicktime']

    for (const file of files) {
      if (!allowedTypes.includes(file.type)) {
        setError(`File type not allowed: ${file.name}`)
        return
      }
      if (file.size > maxSize) {
        setError(`File too large: ${file.name} (max 10MB)`)
        return
      }
    }

    // Create previews
    const newPreviews = files.map((file) => URL.createObjectURL(file))
    setMediaPreviews((prev) => [...prev, ...newPreviews])
    setMediaFiles((prev) => [...prev, ...files])

    // Upload files
    setUploadingMedia(true)
    setError('')

    try {
      const uploadPromises = files.map((file) => uploadMedia(file))
      const results = await Promise.all(uploadPromises)
      const urls = results.map((r) => r.url)
      setMediaUrls((prev) => [...prev, ...urls])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload media')
      // Remove previews for failed uploads
      setMediaPreviews((prev) => prev.slice(0, -files.length))
      setMediaFiles((prev) => prev.slice(0, -files.length))
    } finally {
      setUploadingMedia(false)
    }
  }

  const removeMedia = (index: number) => {
    setMediaFiles((prev) => prev.filter((_, i) => i !== index))
    setMediaUrls((prev) => prev.filter((_, i) => i !== index))
    setMediaPreviews((prev) => {
      URL.revokeObjectURL(prev[index])
      return prev.filter((_, i) => i !== index)
    })
  }

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
      media_urls: mediaUrls,
      post_to_twitter: formData.post_to_twitter,
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

      {/* Media Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Photos/Videos
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/mp4,video/quicktime"
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <div className="flex flex-wrap gap-2 mb-2">
          {mediaPreviews.map((preview, index) => (
            <div key={index} className="relative">
              {mediaFiles[index]?.type.startsWith('video') ? (
                <video
                  src={preview}
                  className="w-20 h-20 object-cover rounded-md"
                />
              ) : (
                <img
                  src={preview}
                  alt={`Preview ${index + 1}`}
                  className="w-20 h-20 object-cover rounded-md"
                />
              )}
              <button
                type="button"
                onClick={() => removeMedia(index)}
                className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center hover:bg-red-600"
              >
                X
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingMedia || mediaPreviews.length >= 4}
            className="w-20 h-20 border-2 border-dashed border-gray-300 rounded-md flex items-center justify-center text-gray-400 hover:border-gray-400 hover:text-gray-500 disabled:opacity-50"
          >
            {uploadingMedia ? (
              <span className="text-xs">...</span>
            ) : (
              <span className="text-2xl">+</span>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500">
          Up to 4 images or videos (max 10MB each)
        </p>
      </div>

      {/* Twitter Posting Option */}
      <div className="bg-blue-50 p-3 rounded-md">
        <label className="flex items-start space-x-3 cursor-pointer">
          <input
            type="checkbox"
            checked={formData.post_to_twitter}
            onChange={(e) =>
              setFormData((prev) => ({ ...prev, post_to_twitter: e.target.checked }))
            }
            className="mt-1 rounded border-gray-300 text-blue-500 focus:ring-blue-500"
          />
          <div>
            <span className="text-sm font-medium text-gray-900 flex items-center">
              <svg className="w-4 h-4 mr-1" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              Post to X (Twitter)
            </span>
            <p className="text-xs text-gray-600 mt-1">
              Automatically @mention the local NWS Weather Forecast Office
            </p>
          </div>
        </label>
      </div>

      {/* Actions */}
      <div className="flex space-x-3 pt-2">
        <button
          type="submit"
          disabled={mutation.isPending || uploadingMedia}
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
