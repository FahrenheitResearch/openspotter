type MessageHandler = (data: any) => void

class WebSocketService {
  private locationSocket: WebSocket | null = null
  private chatSocket: WebSocket | null = null
  private locationHandlers: Map<string, MessageHandler[]> = new Map()
  private chatHandlers: Map<string, MessageHandler[]> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  private getWsUrl(): string {
    return import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
  }

  private getToken(): string | null {
    const authData = localStorage.getItem('openspotter-auth')
    if (authData) {
      try {
        const { state } = JSON.parse(authData)
        return state?.accessToken || null
      } catch {
        return null
      }
    }
    return null
  }

  // Location WebSocket
  connectLocation(): void {
    const token = this.getToken()
    if (!token) {
      console.error('No auth token for WebSocket')
      return
    }

    if (this.locationSocket?.readyState === WebSocket.OPEN) {
      return
    }

    this.locationSocket = new WebSocket(`${this.getWsUrl()}/locations/ws`)

    this.locationSocket.onopen = () => {
      console.log('Location WebSocket connected')
      this.reconnectAttempts = 0
      // Send auth token
      this.locationSocket?.send(JSON.stringify({ token }))
    }

    this.locationSocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        const handlers = this.locationHandlers.get(message.type) || []
        handlers.forEach((handler) => handler(message.data))
      } catch (error) {
        console.error('Failed to parse location message:', error)
      }
    }

    this.locationSocket.onclose = () => {
      console.log('Location WebSocket closed')
      this.attemptReconnect('location')
    }

    this.locationSocket.onerror = (error) => {
      console.error('Location WebSocket error:', error)
    }
  }

  disconnectLocation(): void {
    if (this.locationSocket) {
      this.locationSocket.close()
      this.locationSocket = null
    }
  }

  sendLocationUpdate(data: {
    latitude: number
    longitude: number
    altitude?: number
    accuracy?: number
    heading?: number
    speed?: number
    visibility?: string
  }): void {
    if (this.locationSocket?.readyState === WebSocket.OPEN) {
      this.locationSocket.send(
        JSON.stringify({
          type: 'location_update',
          ...data,
        })
      )
    }
  }

  stopLocationSharing(): void {
    if (this.locationSocket?.readyState === WebSocket.OPEN) {
      this.locationSocket.send(JSON.stringify({ type: 'stop_sharing' }))
    }
  }

  onLocationUpdate(handler: MessageHandler): () => void {
    return this.addHandler(this.locationHandlers, 'location_update', handler)
  }

  onLocationStopped(handler: MessageHandler): () => void {
    return this.addHandler(this.locationHandlers, 'location_stopped', handler)
  }

  // Chat WebSocket
  connectChat(): void {
    const token = this.getToken()
    if (!token) {
      console.error('No auth token for WebSocket')
      return
    }

    if (this.chatSocket?.readyState === WebSocket.OPEN) {
      return
    }

    this.chatSocket = new WebSocket(`${this.getWsUrl()}/messages/ws`)

    this.chatSocket.onopen = () => {
      console.log('Chat WebSocket connected')
      this.reconnectAttempts = 0
      this.chatSocket?.send(JSON.stringify({ token }))
    }

    this.chatSocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        const handlers = this.chatHandlers.get(message.type) || []
        handlers.forEach((handler) => handler(message.data))
      } catch (error) {
        console.error('Failed to parse chat message:', error)
      }
    }

    this.chatSocket.onclose = () => {
      console.log('Chat WebSocket closed')
      this.attemptReconnect('chat')
    }

    this.chatSocket.onerror = (error) => {
      console.error('Chat WebSocket error:', error)
    }
  }

  disconnectChat(): void {
    if (this.chatSocket) {
      this.chatSocket.close()
      this.chatSocket = null
    }
  }

  sendChatMessage(data: {
    content: string
    channel_id?: string
    recipient_id?: string
    latitude?: number
    longitude?: number
  }): void {
    if (this.chatSocket?.readyState === WebSocket.OPEN) {
      this.chatSocket.send(
        JSON.stringify({
          type: 'message',
          ...data,
        })
      )
    }
  }

  joinChannel(channelId: string): void {
    if (this.chatSocket?.readyState === WebSocket.OPEN) {
      this.chatSocket.send(
        JSON.stringify({
          type: 'join_channel',
          channel_id: channelId,
        })
      )
    }
  }

  leaveChannel(channelId: string): void {
    if (this.chatSocket?.readyState === WebSocket.OPEN) {
      this.chatSocket.send(
        JSON.stringify({
          type: 'leave_channel',
          channel_id: channelId,
        })
      )
    }
  }

  onChatMessage(handler: MessageHandler): () => void {
    return this.addHandler(this.chatHandlers, 'chat_message', handler)
  }

  // Helper methods
  private addHandler(
    handlers: Map<string, MessageHandler[]>,
    type: string,
    handler: MessageHandler
  ): () => void {
    if (!handlers.has(type)) {
      handlers.set(type, [])
    }
    handlers.get(type)!.push(handler)

    // Return cleanup function
    return () => {
      const typeHandlers = handlers.get(type)
      if (typeHandlers) {
        const index = typeHandlers.indexOf(handler)
        if (index > -1) {
          typeHandlers.splice(index, 1)
        }
      }
    }
  }

  private attemptReconnect(type: 'location' | 'chat'): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error(`Max reconnect attempts reached for ${type} WebSocket`)
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    setTimeout(() => {
      console.log(`Attempting to reconnect ${type} WebSocket...`)
      if (type === 'location') {
        this.connectLocation()
      } else {
        this.connectChat()
      }
    }, delay)
  }
}

export const wsService = new WebSocketService()
