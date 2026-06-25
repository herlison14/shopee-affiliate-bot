import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useAgentActions() {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [agentEnabled, setAgentEnabled] = useState(true)
  const [settingsLoading, setSettingsLoading] = useState(true)

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

  const fetchSettings = useCallback(async () => {
    setSettingsLoading(true)
    try {
      const { data } = await api.get('/agent/settings')
      setAgentEnabled(data.agent_enabled)
    } finally {
      setSettingsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchActions()
    fetchSettings()
  }, [fetchActions, fetchSettings])

  const toggleAgentEnabled = async (enabled) => {
    const { data } = await api.put('/agent/settings', { agent_enabled: enabled })
    setAgentEnabled(data.agent_enabled)
    return data.agent_enabled
  }

  return {
    actions,
    loading,
    error,
    refetch: fetchActions,
    agentEnabled,
    settingsLoading,
    toggleAgentEnabled,
  }
}
