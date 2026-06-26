import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useStorefront() {
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchSettings = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/storefront/settings')
      setSettings(data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar vitrine')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSettings()
  }, [fetchSettings])

  const updateSettings = async (storefront_name, storefront_bio) => {
    const { data } = await api.put('/storefront/settings', { storefront_name, storefront_bio })
    setSettings(data)
    return data
  }

  return { settings, loading, error, updateSettings }
}
