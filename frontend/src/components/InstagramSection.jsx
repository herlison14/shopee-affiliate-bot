import { useState } from 'react'

// Seção do dashboard pra conectar a conta do Instagram. O usuário obtém o token
// de longa duração no Meta for Developers (OAuth) e cola aqui junto do IG
// Business Account ID. Publicação só funciona após a App Review da Meta liberar
// instagram_content_publish.
export default function InstagramSection({ instagram }) {
  const { connected, username, loading, error, connect } = instagram
  const [token, setToken] = useState('')
  const [igUserId, setIgUserId] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState(null)

  const handleConnect = async (e) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await connect(token.trim(), igUserId.trim())
      setToken('')
      setIgUserId('')
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Não foi possível conectar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="mb-8 rounded-xl bg-white p-5 shadow-sm sm:p-6">
      <div className="mb-1 flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold">Instagram</h2>
        <span
          className={`whitespace-nowrap rounded-full px-3 py-1 text-xs font-semibold ${
            connected ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {loading ? '...' : connected ? `Conectado${username ? ` · @${username}` : ''}` : 'Não conectado'}
        </span>
      </div>
      <p className="mb-4 text-sm text-gray-500">
        Conecte sua conta profissional do Instagram pra publicar campanhas direto daqui.
        Requer a conta vinculada a uma Página do Facebook e um token de longa duração
        gerado no Meta for Developers.
      </p>

      {connected ? (
        <p className="text-sm text-gray-600">
          Conta conectada{username ? ` como @${username}` : ''}. Use o botão “Postar no
          Instagram” em cada campanha (precisa ter imagem).
        </p>
      ) : (
        <form onSubmit={handleConnect} className="grid gap-3 sm:grid-cols-2">
          <input
            type="text"
            aria-label="Token de acesso do Instagram"
            placeholder="Token de acesso (longa duração)"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm"
          />
          <input
            type="text"
            aria-label="Instagram Business Account ID"
            placeholder="IG Business Account ID"
            required
            value={igUserId}
            onChange={(e) => setIgUserId(e.target.value)}
            className="rounded-lg border px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-shopee-dark px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 sm:col-span-2"
          >
            {saving ? 'Conectando...' : 'Conectar Instagram'}
          </button>
        </form>
      )}
      {(formError || (error && !connected)) && (
        <p className="mt-2 text-sm text-red-600">{formError || error}</p>
      )}
    </section>
  )
}
