import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import { AuthProvider } from './auth';
import { GreenhouseProvider } from './greenhouse';
import { I18nProvider } from './i18n';
import { ThemeProvider } from './theme';
import { App } from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <I18nProvider>
        <AuthProvider>
          <GreenhouseProvider>
            <App />
          </GreenhouseProvider>
        </AuthProvider>
      </I18nProvider>
    </ThemeProvider>
  </StrictMode>
);
