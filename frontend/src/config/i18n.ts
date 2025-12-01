import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import esCO from '../locales/es-CO.json'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      'es-CO': {
        translation: esCO,
      },
    },
    lng: 'es-CO',
    fallbackLng: 'es-CO',
    interpolation: {
      escapeValue: false, // React already escapes values
    },
    react: {
      useSuspense: false, // Disable suspense for better compatibility
    },
  })

export default i18n

