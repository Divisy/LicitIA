import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout'
import Dashboard from './pages/Dashboard'
import Profile from './pages/Profile'
import Experiences from './pages/Experiences'
import Support from './pages/Support'
import Feedback from './pages/Feedback'
import Landing from './pages/Landing'
import Login from './pages/Login'

function App() {
  return (
    <Routes>
      {/* Landing page as root - without layout */}
      <Route path="/" element={<Landing />} />
      <Route path="/landing" element={<Navigate to="/" replace />} />
      
      {/* Login page without layout */}
      <Route path="/login" element={<Login />} />
      
      {/* App routes with Carbon layout */}
      <Route
        path="/*"
        element={
          <AppLayout>
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/experiences" element={<Experiences />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/help" element={<Support />} />
              <Route path="/feedback" element={<Feedback />} />
              {/* Redirect old / route to dashboard for existing users */}
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </AppLayout>
        }
      />
    </Routes>
  )
}

export default App

