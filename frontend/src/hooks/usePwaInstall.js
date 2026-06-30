import { useEffect, useState } from 'react'

// Detecta se o app ja esta rodando instalado (standalone) -- nesse caso nao
// faz sentido oferecer instalacao.
function isStandalone() {
  return (
    window.matchMedia?.('(display-mode: standalone)').matches ||
    window.navigator.standalone === true
  )
}

function isIos() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent)
}

// Encapsula o fluxo de "Adicionar a tela inicial":
// - Android/Chrome dispara 'beforeinstallprompt'; guardamos o evento e
//   chamamos prompt() quando o usuario clicar.
// - iOS/Safari nao tem essa API -- expomos uma flag pra mostrar instrucoes.
export function usePwaInstall() {
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [installed, setInstalled] = useState(isStandalone())

  useEffect(() => {
    const onBeforeInstall = (e) => {
      e.preventDefault() // impede o mini-infobar nativo; controlamos o momento
      setDeferredPrompt(e)
    }
    const onInstalled = () => {
      setInstalled(true)
      setDeferredPrompt(null)
    }
    window.addEventListener('beforeinstallprompt', onBeforeInstall)
    window.addEventListener('appinstalled', onInstalled)
    return () => {
      window.removeEventListener('beforeinstallprompt', onBeforeInstall)
      window.removeEventListener('appinstalled', onInstalled)
    }
  }, [])

  const promptInstall = async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') setInstalled(true)
    setDeferredPrompt(null)
  }

  return {
    installed,
    canInstall: !installed && !!deferredPrompt, // Android/Chrome
    showIosHint: !installed && isIos() && !deferredPrompt, // iOS/Safari
    promptInstall,
  }
}
