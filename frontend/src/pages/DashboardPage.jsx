import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useCampaigns } from '../hooks/useCampaigns'

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const { campaigns, loading, error, createCampaign, deleteCampaign } = useCampaigns()
  const [productName, setProductName] = useState('')
  const [productUrl, setProductUrl] = useState('')
  const [affiliateLink, setAffiliateLink] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  const handleCreate = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setFormError(null)
    try {
      await createCampaign({
        product_name: productName,
        product_url: productUrl,
        affiliate_link: affiliateLink || null,
      })
      setProductName('')
      setProductUrl('')
      setAffiliateLink('')
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Erro ao criar campanha')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between bg-white px-6 py-4 shadow-sm">
        <h1 className="text-xl font-bold text-shopee">ShopeeViral.AI</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.full_name || user?.email}</span>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-shopee">
            Sair
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-8">
        <section className="mb-8 rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Nova campanha</h2>
          <form onSubmit={handleCreate} className="grid gap-3 sm:grid-cols-3">
            <input
              type="text"
              placeholder="Nome do produto"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <input
              type="url"
              placeholder="URL do produto na Shopee"
              required
              value={productUrl}
              onChange={(e) => setProductUrl(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <input
              type="url"
              placeholder="Link de afiliado (opcional)"
              value={affiliateLink}
              onChange={(e) => setAffiliateLink(e.target.value)}
              className="rounded-lg border px-3 py-2 text-sm sm:col-span-1"
            />
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-shopee px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-50 sm:col-span-3"
            >
              {submitting ? 'Gerando legenda com IA...' : 'Criar campanha'}
            </button>
          </form>
          {formError && <p className="mt-2 text-sm text-red-500">{formError}</p>}
        </section>

        <section className="rounded-xl bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Campanhas</h2>
          {loading && <p className="text-sm text-gray-500">Carregando...</p>}
          {error && <p className="text-sm text-red-500">{error}</p>}
          {!loading && campaigns.length === 0 && (
            <p className="text-sm text-gray-500">Nenhuma campanha criada ainda.</p>
          )}
          <ul className="space-y-3">
            {campaigns.map((c) => (
              <li key={c.id} className="rounded-lg border p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{c.product_name}</p>
                    <p className="text-sm text-gray-600">{c.caption}</p>
                    <p className="text-xs text-gray-400">{c.hashtags}</p>
                    <span className="mt-1 inline-block rounded bg-gray-100 px-2 py-0.5 text-xs">
                      {c.status}
                    </span>
                  </div>
                  <button
                    onClick={() => deleteCampaign(c.id)}
                    className="text-xs text-red-500 hover:underline"
                  >
                    Remover
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  )
}
