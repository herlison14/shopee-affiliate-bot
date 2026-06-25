import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useAgentActions() {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchActions = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/agent/actions')
      setActions(data)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar historico do agente')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchActions()
  }, [fetchActions])

  return { actions, loading, error, refetch: fetchActions }
}
