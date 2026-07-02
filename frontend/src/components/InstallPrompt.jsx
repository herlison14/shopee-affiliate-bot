import { useState } from 'react'
import { usePwaInstall } from '../hooks/usePwaInstall'

const DISMISS_KEY = 'pwa_install_dismissed'

// Banner que convida a instalar o app no celular. Aparece so quando da pra
// instalar (Android/Chrome) ou no iOS/Safari (com instrucoes), e some quando
// o app ja esta instalado ou o usuario dispensa. Nao volta a aparecer depois
// de dispensado (flag no localStorage).
export default function InstallPrompt() {
  const { canInstall, showIosHint, promptInstall } = usePwaInstall()
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem(DISMISS_KEY) === '1',
  )

  if (dismissed || (!canInstall && !showIosHint)) return null

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, '1')
    setDismissed(true)
  }

  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-orange-100 bg-orange-50 p-4">
      <span className="text-2xl leading-none">📱</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-gray-900">Instale o app no seu celular</p>
        {canInstall ? (
          <>
            <p className="mt-0.5 text-sm text-gray-600">
              Acesso rápido em tela cheia, direto da tela inicial — sem abrir o navegador.
            </p>
            <button
              onClick={promptInstall}
              className="mt-2 rounded-lg bg-shopee-dark px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
            >
              Instalar app
            </button>
          </>
        ) : (
          <p className="mt-0.5 text-sm text-gray-600">
            No iPhone: toque em <span className="font-medium">Compartilhar</span>{' '}
            <span aria-hidden>⎙</span> e depois em{' '}
            <span className="font-medium">"Adicionar à Tela de Início"</span>.
          </p>
        )}
      </div>
      <button
        onClick={dismiss}
        aria-label="Dispensar"
        className="shrink-0 rounded p-1 text-gray-500 hover:text-gray-600"
      >
        ✕
      </button>
    </div>
  )
}
