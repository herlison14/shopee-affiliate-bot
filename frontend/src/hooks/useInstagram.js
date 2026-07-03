import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useInstagram() {
  const [connected, setConnected] = useState(false)
  const [username, setUsername] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatus = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/instagram/status')
      setConnected(data.connected)
      setUsername(data.username || null)
      setError(data.connected ? null : data.detail || null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao consultar Instagram')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  const connect = async (accessToken, instagramUserId) => {
    const { data } = await api.post('/instagram/connect', {
      access_token: accessToken,
      instagram_user_id: instagramUserId,
    })
    setConnected(data.connected)
    setUsername(data.username || null)
    return data
  }

  const publish = async (campaignId) => {
    const { data } = await api.post(`/instagram/campaigns/${campaignId}/publish`)
    return data
  }

  return { connected, username, loading, error, fetchStatus, connect, publish }
}
