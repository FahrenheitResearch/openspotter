import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import clsx from 'clsx'
import { format } from 'date-fns'

const reportTypes = [
  { value: '', label: 'All Types' },
  { value: 'tornado', label: 'Tornado' },
  { value: 'funnel_cloud', label: 'Funnel Cloud' },
  { value: 'wall_cloud', label: 'Wall Cloud' },
  { value: 'hail', label: 'Hail' },
  { value: 'wind_damage', label: 'Wind Damage' },
  { value: 'flooding', label: 'Flooding' },
  { value: 'wildfire', label: 'Wildfire' },
  { value: 'other', label: 'Other' },
]

interface Report {
  id: string
  type: string
  title: string | null
  description: string | null
  latitude: number
  longitude: number
  severity: number | null
  hail_size: number | null
  wind_speed: number | null
  tornado_rating: string | null
  is_verified: boolean
  created_at: string
  reporter: {
    id: string
    callsign: string | null
    role: string
  } | null
}

export default function Reports() {
  const [filters, setFilters] = useState({
    type: '',
    hours: 24,
    verified_only: false,
  })
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['reports-list', filters, page],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.type) params.set('report_type', filters.type)
      params.set('hours', filters.hours.toString())
      if (filters.verified_only) params.set('verified_only', 'true')
      params.set('page', page.toString())
      params.set('per_page', '20')

      const response = await api.get(`/reports?${params}`)
      return response.data
    },
  })

  const reports: Report[] = data?.reports || []
  const totalPages = Math.ceil((data?.total || 0) / 20)

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Weather Reports</h1>

      {/* Filters */}
      <div className="bg-white shadow rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={filters.type}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, type: e.target.value }))
              }
              className="px-3 py-2 border rounded-md text-sm"
            >
              {reportTypes.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time Range
            </label>
            <select
              value={filters.hours}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  hours: parseInt(e.target.value),
                }))
              }
              className="px-3 py-2 border rounded-md text-sm"
            >
              <option value={6}>Last 6 hours</option>
              <option value={12}>Last 12 hours</option>
              <option value={24}>Last 24 hours</option>
              <option value={48}>Last 48 hours</option>
              <option value={168}>Last 7 days</option>
            </select>
          </div>

          <div className="flex items-end">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={filters.verified_only}
                onChange={(e) =>
                  setFilters((prev) => ({
                    ...prev,
                    verified_only: e.target.checked,
                  }))
                }
                className="rounded"
              />
              <span className="text-sm">Verified only</span>
            </label>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-500">Loading reports...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No reports found matching your filters
        </div>
      ) : (
        <>
          <div className="bg-white shadow rounded-lg overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Details
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Location
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reporter
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={clsx(
                          'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                          report.type === 'tornado' &&
                            'bg-red-100 text-red-800',
                          report.type === 'hail' &&
                            'bg-purple-100 text-purple-800',
                          report.type === 'flooding' &&
                            'bg-blue-100 text-blue-800',
                          report.type === 'wind_damage' &&
                            'bg-cyan-100 text-cyan-800',
                          report.type === 'wildfire' &&
                            'bg-orange-100 text-orange-800',
                          !['tornado', 'hail', 'flooding', 'wind_damage', 'wildfire'].includes(
                            report.type
                          ) && 'bg-gray-100 text-gray-800'
                        )}
                      >
                        {report.type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        {report.title || report.description?.slice(0, 50) || '-'}
                      </div>
                      <div className="text-xs text-gray-500">
                        {report.severity && `Severity: ${report.severity}/5`}
                        {report.hail_size && ` | Hail: ${report.hail_size}"`}
                        {report.wind_speed && ` | Wind: ${report.wind_speed} mph`}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {report.latitude.toFixed(4)}, {report.longitude.toFixed(4)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {report.reporter?.callsign || 'Anonymous'}
                      </div>
                      <div className="text-xs text-gray-500 capitalize">
                        {report.reporter?.role?.replace('_', ' ')}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {format(new Date(report.created_at), 'MMM d, h:mm a')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {report.is_verified ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Verified
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                          Unverified
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center space-x-2 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded-md disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-3 py-1">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border rounded-md disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
