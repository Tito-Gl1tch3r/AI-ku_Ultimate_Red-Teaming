import React, { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import Layout from './components/Layout'

const Login = lazy(() => import('./pages/Login'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Servers = lazy(() => import('./pages/Servers'))
const Profiles = lazy(() => import('./pages/Profiles'))
const Templates = lazy(() => import('./pages/Templates'))
const Lists = lazy(() => import('./pages/Lists'))
const Campaigns = lazy(() => import('./pages/Campaigns'))
const CampaignDetail = lazy(() => import('./pages/CampaignDetail'))
const Config = lazy(() => import('./pages/Config'))
const Account = lazy(() => import('./pages/Account'))
const Unauthorized = lazy(() => import('./pages/Unauthorized'))
const ServerError = lazy(() => import('./pages/ServerError'))
const NotFound = lazy(() => import('./pages/NotFound'))

function Protected({ children }){
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App(){
  const [dark, setDark] = useState(true)

  useEffect(()=>{
    setDark((localStorage.getItem('theme')||'dark')==='dark')
  },[])

  useEffect(()=>{
    const root = document.documentElement
    if (dark){ root.classList.add('dark'); localStorage.setItem('theme','dark') }
    else { root.classList.remove('dark'); localStorage.setItem('theme','light') }
  }, [dark])

  return (
    <div className="min-h-screen">
      <Suspense fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-slate-600 dark:text-slate-400">Loading...</div>
        </div>
      }>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <Protected>
              <Layout onThemeToggle={()=>setDark(v=>!v)} dark={dark}>
                <Routes>
                  <Route index element={<Dashboard />} />
                  <Route path="servers" element={<Servers />} />
                  <Route path="profiles" element={<Profiles />} />
                  <Route path="templates" element={<Templates />} />
                  <Route path="lists" element={<Lists />} />
                  <Route path="campaigns" element={<Campaigns />} />
                  <Route path="campaigns/:id" element={<CampaignDetail />} />
                  <Route path="config" element={<Config />} />
                  <Route path="account" element={<Account />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Layout>
            </Protected>
          } />
          <Route path="/unauthorized" element={<Unauthorized />} />
          <Route path="/server-error" element={<ServerError />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
      <ToastContainer position="top-center" theme={dark ? 'dark' : 'light'} />
    </div>
  )
}