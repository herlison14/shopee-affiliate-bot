import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useCampaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchCampaigns = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/campaigns')
      setCampaigns(data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar campanhas')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCampaigns()
  }, [fetchCampaigns])

  const createCampaign = async (payload) => {
    const { data } = await api.post('/campaigns', payload)
    setCampaigns((prev) => [data, ...prev])
    return data
  }

  const deleteCampaign = async (id) => {
    await api.delete(`/campaigns/${id}`)
    setCampaigns((prev) => prev.filter((c) => c.id !== id))
  }

  return { campaigns, loading, error, fetchCampaigns, createCampaign, deleteCampaign }
}
