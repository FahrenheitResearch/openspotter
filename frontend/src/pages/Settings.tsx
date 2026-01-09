import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useAuthStore } from '../store/auth'
import { api } from '../services/api'

export default function Settings() {
  const { user, updateUser } = useAuthStore()
  const [formData, setFormData] = useState({
    callsign: user?.callsign || '',
    display_name: user?.display_name || '',
    share_location_with: user?.share_location_with || 'public',
  })
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: (data: typeof formData) => api.patch('/users/me', data),
    onSuccess: (response) => {
      updateUser(response.data)
      setSuccess('Settings saved successfully')
      setError('')
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to save settings')
      setSuccess('')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate(formData)
  }

  const handleExportData = async () => {
    try {
      const response = await api.get('/users/me/export')
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'openspotter-data-export.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Failed to export data')
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {/* Profile section */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium mb-4">Profile</h2>

        {success && (
          <div className="bg-green-50 text-green-700 p-3 rounded-md text-sm mb-4">
            {success}
          </div>
        )}

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Email
            </label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Callsign
            </label>
            <input
              type="text"
              value={formData.callsign}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, callsign: e.target.value }))
              }
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Display Name
            </label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  display_name: e.target.value,
                }))
              }
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white py-2 px-4 rounded-md font-medium disabled:opacity-50"
          >
            {mutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      {/* Privacy section */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium mb-4">Privacy</h2>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Share my location with
          </label>
          <select
            value={formData.share_location_with}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                share_location_with: e.target.value,
              }))
            }
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
          >
            <option value="public">Everyone (public)</option>
            <option value="verified">Verified spotters and above</option>
            <option value="coordinators">Coordinators only</option>
          </select>
          <p className="mt-1 text-xs text-gray-500">
            Controls who can see your location when you&apos;re sharing
          </p>
        </div>
      </div>

      {/* Account info */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium mb-4">Account</h2>

        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-500">Role</span>
            <span className="font-medium capitalize">
              {user?.role?.replace('_', ' ')}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">Email Verified</span>
            <span
              className={
                user?.is_email_verified ? 'text-green-600' : 'text-yellow-600'
              }
            >
              {user?.is_email_verified ? 'Yes' : 'No'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-500">2FA Enabled</span>
            <span
              className={
                user?.totp_enabled ? 'text-green-600' : 'text-gray-400'
              }
            >
              {user?.totp_enabled ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>

      {/* Data export */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-lg font-medium mb-4">Your Data</h2>
        <p className="text-sm text-gray-600 mb-4">
          You own your data. Export all your data including location history,
          reports, and messages at any time.
        </p>
        <button
          onClick={handleExportData}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 px-4 rounded-md font-medium"
        >
          Export My Data
        </button>
      </div>

      {/* Danger zone */}
      <div className="bg-white shadow rounded-lg p-6 border-2 border-red-200">
        <h2 className="text-lg font-medium text-red-600 mb-4">Danger Zone</h2>
        <p className="text-sm text-gray-600 mb-4">
          Permanently delete your account and all associated data. This action
          cannot be undone.
        </p>
        <button className="bg-red-600 hover:bg-red-700 text-white py-2 px-4 rounded-md font-medium">
          Delete Account
        </button>
      </div>
    </div>
  )
}
