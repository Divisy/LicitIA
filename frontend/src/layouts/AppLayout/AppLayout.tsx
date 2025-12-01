import React, { ReactNode, useState, useRef, useEffect } from 'react'
import { 
  Header, 
  HeaderName, 
  HeaderGlobalBar, 
  HeaderGlobalAction,
  Button
} from '@carbon/react'
import { 
  WatsonMachineLearning,
  Switcher, 
  User, 
  Settings,
  Help,
  Logout,
  Dashboard as DashboardIcon,
  DocumentAdd,
  ChevronDown,
  Close,
  Search,
  Chat
} from '@carbon/icons-react'
import { useTranslation } from 'react-i18next'
import { useTheme } from '../../theme/ThemeProvider'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import Logo from '../../components/Logo'
import FeedbackWidget from '../../components/FeedbackWidget'
import './AppLayout.scss'

interface AppLayoutProps {
  children: ReactNode
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const { t } = useTranslation()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [isSideNavExpanded, setIsSideNavExpanded] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [sidebarSearch, setSidebarSearch] = useState('')
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Get user info from localStorage
  const userName = localStorage.getItem('licitia_user_name') || 'Usuario'
  const userInitials = userName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2) || 'U'

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false)
      }
    }

    if (isUserMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isUserMenuOpen])

  const isActive = (path: string) => location.pathname === path

  const handleLogoClick = () => {
    navigate('/dashboard')
    setIsSideNavExpanded(false)
  }

  const handleLogout = () => {
    // Clear all user data from localStorage
    localStorage.removeItem('licitia_user_email')
    localStorage.removeItem('licitia_user_name')
    localStorage.removeItem('licitia_user_company')
    localStorage.removeItem('licitia_user_industry')
    localStorage.removeItem('licitia_user_company_size')
    localStorage.removeItem('licitia_user_role')
    localStorage.removeItem('licitia_new_user')
    localStorage.removeItem('licitia_onboarding_completed')
    localStorage.removeItem('licitia_onboarding_state')
    localStorage.removeItem('licitia_onboarding_banner_dismissed')
    localStorage.removeItem('licitia_start_onboarding')
    
    // Navigate to landing page
    navigate('/landing')
  }

  const navigationItems = [
    { id: 'dashboard', label: 'Inicio', icon: DashboardIcon, path: '/', exact: true },
    { id: 'experiences', label: 'Experiencias', icon: DocumentAdd, path: '/experiences' },
    { id: 'profile', label: 'Perfil', icon: User, path: '/profile' },
    { id: 'feedback', label: 'Feedback', icon: Chat, path: '/feedback' },
    { id: 'help', label: 'Soporte', icon: Help, path: '/help' },
  ]

  const filteredNavItems = navigationItems.filter(item =>
    item.label.toLowerCase().includes(sidebarSearch.toLowerCase())
  )

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className={`app-sidebar ${isSidebarCollapsed ? 'app-sidebar--collapsed' : ''}`}>
        <div className="app-sidebar__header">
          <Logo 
            size="sm" 
            showText={!isSidebarCollapsed}
            className="app-sidebar__logo"
          />
          <button
            className="app-sidebar__close"
            onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
            aria-label={isSidebarCollapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
          >
            <Close size={16} />
          </button>
        </div>

        {!isSidebarCollapsed && (
          <>
            <div className="app-sidebar__search">
              <div className="app-sidebar__search-wrapper">
                <Search size={16} className="app-sidebar__search-icon" />
                <input
                  type="text"
                  className="app-sidebar__search-input"
                  placeholder="Filtrar navegación"
                  value={sidebarSearch}
                  onChange={(e) => setSidebarSearch(e.target.value)}
                />
              </div>
              <button
                className="app-sidebar__collapse-button"
                onClick={() => setIsSidebarCollapsed(true)}
                aria-label="Colapsar sidebar"
              >
                <ChevronDown size={16} style={{ transform: 'rotate(-90deg)' }} />
              </button>
            </div>

            <nav className="app-sidebar__nav">
              {filteredNavItems.map((item) => {
                const Icon = item.icon
                const isActive = item.exact 
                  ? location.pathname === item.path
                  : location.pathname.startsWith(item.path) && item.path !== '/'
                
                return (
                  <button
                    key={item.id}
                    className={`app-sidebar__nav-item ${isActive ? 'app-sidebar__nav-item--active' : ''}`}
                    onClick={() => {
                      navigate(item.path)
                      setIsSidebarCollapsed(false)
                    }}
                    title={item.label}
                  >
                    <Icon size={20} className="app-sidebar__nav-icon" />
                    <span className="app-sidebar__nav-label">{item.label}</span>
                    <ChevronDown size={16} className="app-sidebar__nav-chevron" />
                  </button>
                )
              })}
            </nav>
          </>
        )}
      </aside>

      <div className={`app-content ${isSidebarCollapsed ? 'app-content--sidebar-collapsed' : ''}`}>
      <Header aria-label="LicitIA" className="app-header">
        <HeaderGlobalAction
          aria-label="Abrir menú"
          className="app-header__menu-toggle"
          onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          isActive={!isSidebarCollapsed}
        >
          <Switcher size={20} />
        </HeaderGlobalAction>
        
        <HeaderName
          prefix=""
          onClick={handleLogoClick}
          className="app-header__name"
        >
          <Logo size="sm" showText={true} className="app-header__logo" />
        </HeaderName>

        <HeaderGlobalBar className="app-header__global-bar">
          {/* Primary Action Button */}
          <Button
            kind="primary"
            size="sm"
            onClick={() => navigate('/experiences')}
            className="app-header__primary-button"
          >
            Actualizar Experiencias
          </Button>

          {/* User Menu */}
          <div className="app-header__user-menu-wrapper" ref={userMenuRef}>
            <button
              className="app-header__user-menu-button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              aria-label="Menú de usuario"
            >
              <div className="app-header__user-avatar">
                {userInitials}
              </div>
              <span className="app-header__user-name">{userName}</span>
              <ChevronDown 
                size={16} 
                className={`app-header__user-chevron ${isUserMenuOpen ? 'app-header__user-chevron--open' : ''}`}
              />
            </button>
            
            {isUserMenuOpen && (
              <div className="app-header__user-menu-dropdown">
                <button
                  className="app-header__user-menu-item"
                  onClick={() => {
                    navigate('/profile')
                    setIsUserMenuOpen(false)
                  }}
                >
                  <User size={16} />
                  <span>Perfil</span>
                </button>
                <button
                  className="app-header__user-menu-item"
                  onClick={() => {
                    // TODO: Navigate to settings
                    console.log('Settings clicked')
                    setIsUserMenuOpen(false)
                  }}
                >
                  <Settings size={16} />
                  <span>Configuración</span>
                </button>
                <div className="app-header__user-menu-divider"></div>
                <button
                  className="app-header__user-menu-item app-header__user-menu-item--danger"
                  onClick={handleLogout}
                >
                  <Logout size={16} />
                  <span>Cerrar sesión</span>
                </button>
              </div>
            )}
          </div>

          {/* App Launcher */}
          <HeaderGlobalAction
            aria-label="Aplicaciones"
            tooltipAlignment="end"
            onClick={() => {
              // TODO: Open app launcher
              console.log('App launcher clicked')
            }}
            className="app-header__action app-header__action--launcher"
          >
            <Switcher size={20} />
          </HeaderGlobalAction>
        </HeaderGlobalBar>

      </Header>
      
      <main className="app-main">
        {children}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <div className="app-footer__content">
          <Logo size="sm" showText={true} />
          <div className="app-footer__links">
            <a href="/help" className="app-footer__link">Ayuda</a>
            <a href="/settings" className="app-footer__link">Configuración</a>
            <a href="https://docs.licitia.co" target="_blank" rel="noopener noreferrer" className="app-footer__link">Documentación</a>
          </div>
          <p className="app-footer__copyright">
            © {new Date().getFullYear()} LicitIA. Todos los derechos reservados.
          </p>
        </div>
      </footer>

      {/* Feedback Widget - Available on all pages */}
      <FeedbackWidget />
      </div>
    </div>
  )
}

export default AppLayout
