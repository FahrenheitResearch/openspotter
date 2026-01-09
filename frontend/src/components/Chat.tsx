import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchChannels, fetchChannelMessages } from '../services/api'
import { wsService } from '../services/websocket'
import { useAuthStore } from '../store/auth'
import clsx from 'clsx'

interface Message {
  id: string
  content: string
  sender: {
    id: string
    callsign: string | null
    role: string
  }
  channel_id: string | null
  created_at: string
}

interface Channel {
  id: string
  name: string
  description: string | null
}

export default function Chat() {
  const { isAuthenticated, user } = useAuthStore()
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Fetch channels
  const { data: channelsData } = useQuery({
    queryKey: ['channels'],
    queryFn: fetchChannels,
    enabled: isAuthenticated,
  })

  // Fetch messages when channel changes
  const { data: messagesData } = useQuery({
    queryKey: ['messages', selectedChannel],
    queryFn: () => fetchChannelMessages(selectedChannel!),
    enabled: !!selectedChannel,
  })

  // Initialize messages from query
  useEffect(() => {
    if (messagesData?.messages) {
      setMessages(messagesData.messages.reverse())
    }
  }, [messagesData])

  // Connect to chat WebSocket
  useEffect(() => {
    if (!isAuthenticated) return

    wsService.connectChat()

    const cleanup = wsService.onChatMessage((data) => {
      if (data.channel_id === selectedChannel) {
        setMessages((prev) => [...prev, data])
      }
    })

    return () => {
      cleanup()
      wsService.disconnectChat()
    }
  }, [isAuthenticated, selectedChannel])

  // Join channel when selected
  useEffect(() => {
    if (selectedChannel) {
      wsService.joinChannel(selectedChannel)
    }
  }, [selectedChannel])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newMessage.trim() || !selectedChannel) return

    wsService.sendChatMessage({
      content: newMessage,
      channel_id: selectedChannel,
    })
    setNewMessage('')
  }

  if (!isAuthenticated) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500">
        Login to access chat
      </div>
    )
  }

  const channels: Channel[] = channelsData?.channels || []

  return (
    <div className="h-full flex flex-col bg-white rounded-lg shadow">
      {/* Channel selector */}
      <div className="p-3 border-b">
        <select
          value={selectedChannel || ''}
          onChange={(e) => setSelectedChannel(e.target.value || null)}
          className="w-full px-3 py-2 border rounded-md text-sm"
        >
          <option value="">Select a channel...</option>
          {channels.map((channel) => (
            <option key={channel.id} value={channel.id}>
              #{channel.name}
            </option>
          ))}
        </select>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {!selectedChannel ? (
          <p className="text-gray-500 text-center py-8">
            Select a channel to start chatting
          </p>
        ) : messages.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            No messages yet. Be the first to say something!
          </p>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={clsx(
                'flex',
                msg.sender.id === user?.id ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={clsx(
                  'max-w-[80%] rounded-lg px-3 py-2',
                  msg.sender.id === user?.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100'
                )}
              >
                <div className="flex items-center space-x-2 mb-1">
                  <span
                    className={clsx(
                      'text-xs font-medium',
                      msg.sender.id === user?.id
                        ? 'text-primary-100'
                        : 'text-gray-500'
                    )}
                  >
                    {msg.sender.callsign || 'Anonymous'}
                  </span>
                  <span
                    className={clsx(
                      'text-xs capitalize',
                      msg.sender.id === user?.id
                        ? 'text-primary-200'
                        : 'text-gray-400'
                    )}
                  >
                    {msg.sender.role.replace('_', ' ')}
                  </span>
                </div>
                <p className="text-sm">{msg.content}</p>
                <p
                  className={clsx(
                    'text-xs mt-1',
                    msg.sender.id === user?.id
                      ? 'text-primary-200'
                      : 'text-gray-400'
                  )}
                >
                  {new Date(msg.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Message input */}
      {selectedChannel && (
        <form onSubmit={handleSend} className="p-3 border-t">
          <div className="flex space-x-2">
            <input
              type="text"
              value={newMessage}
              onChange={(e) => setNewMessage(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 px-3 py-2 border rounded-md text-sm"
            />
            <button
              type="submit"
              disabled={!newMessage.trim()}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md text-sm font-medium disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
