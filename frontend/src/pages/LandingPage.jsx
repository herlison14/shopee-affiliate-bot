import { Link } from 'react-router-dom'

const FEATURES = [
  {
    title: 'Legenda e hashtags por IA',
    description:
      'Cole o link do produto e o Claude gera legenda viral e hashtags em português, prontas para postar.',
  },
  {
    title: 'James, o agente autônomo',
    description:
      'Roda em background: promove rascunhos esquecidos, renova legendas sem vendas e sugere replicar campanhas de sucesso — sem você pedir.',
  },
  {
    title: 'Converse com a IA',
    description:
      'Cole sua URL pessoal no Claude Desktop ou ChatGPT e peça por conversa: criar campanha, ver comissões, ligar ou desligar o James.',
  },
  {
    title: 'Comissão rastreada automaticamente',
    description:
      'Cada venda gerada pelo seu link de afiliado é registrada e contabilizada, sem planilha manual.',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="flex items-center justify-between px-4 py-5 pt-[calc(1.25rem+env(safe-area-inset-top))] px-safe sm:px-6">
        <span className="text-xl font-bold text-shopee">ShopeeViral.AI</span>
        <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-shopee">
          Entrar
        </Link>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 pt-10 text-center px-safe sm:px-6">
        <span className="mb-4 inline-block rounded-full bg-orange-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-shopee">
          Plataforma de IA para afiliados Shopee
        </span>
        <h1 className="mb-4 text-3xl font-extrabold leading-tight text-gray-900 sm:text-5xl">
          Suas campanhas de afiliado, <span className="text-shopee">criadas por IA</span>
        </h1>
        <p className="mb-8 text-lg text-gray-600">
          Cole o link do produto, a IA escreve a legenda e as hashtags, e o agente James cuida do
          resto em background. Você acompanha tudo pelo painel ou conversando direto com o Claude.
        </p>
        <div className="flex justify-center gap-3">
          <Link
            to="/login"
            className="rounded-lg bg-shopee px-6 py-3 text-sm font-semibold text-white hover:opacity-90"
          >
            Começar agora →
          </Link>
        </div>

        <div className="mt-16 grid gap-4 text-left sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-xl border bg-white p-5 shadow-sm">
              <h2 className="mb-1 font-semibold text-gray-900">{f.title}</h2>
              <p className="text-sm text-gray-600">{f.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-16 rounded-xl bg-white p-6 text-left shadow-sm">
          <h2 className="mb-3 font-semibold text-gray-900">Como funciona</h2>
          <ol className="space-y-2 text-sm text-gray-600">
            <li>
              <strong className="text-gray-900">1.</strong> Crie sua conta gratuita e cole o link
              de um produto Shopee.
            </li>
            <li>
              <strong className="text-gray-900">2.</strong> A IA gera legenda e hashtags na hora —
              você revisa e posta.
            </li>
            <li>
              <strong className="text-gray-900">3.</strong> James acompanha suas campanhas e age
              automaticamente quando precisa.
            </li>
            <li>
              <strong className="text-gray-900">4.</strong> Vendas geradas pelo seu link são
              rastreadas e contabilizadas como comissão.
            </li>
          </ol>
        </div>
      </main>
    </div>
  )
}
