import { useCallback, useEffect, useState } from 'react'
import api from '../lib/api'

export function useMcpUrl() {
  const [mcpUrl, setMcpUrl] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchMcpUrl = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/auth/mcp-url')
      setMcpUrl(data.mcp_url)
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao carregar URL do MCP')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMcpUrl()
  }, [fetchMcpUrl])

  const regenerate = async () => {
    const { data } = await api.post('/auth/mcp-url/regenerate')
    setMcpUrl(data.mcp_url)
    return data.mcp_url
  }

  return { mcpUrl, loading, error, regenerate }
}
