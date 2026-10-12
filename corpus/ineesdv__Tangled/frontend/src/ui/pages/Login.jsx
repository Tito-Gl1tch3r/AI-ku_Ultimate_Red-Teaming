import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { motion } from 'framer-motion'
import { CircleUserRound, Lock, Sun, Moon, ArrowRight } from 'lucide-react'

export default function Login({ onThemeToggle }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isDark, setIsDark] = useState(false)
  const navigate = useNavigate()

  // Theme
  const applyTheme = (mode) => {
    const root = document.documentElement
    const dark = mode === 'dark'
    root.classList.toggle('dark', dark)
    root.style.colorScheme = dark ? 'dark' : 'light'
    localStorage.setItem('theme', mode)
  }

  useEffect(() => {
    // Read saved theme or system preference
    const saved = localStorage.getItem('theme')
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    const mode = saved || (prefersDark ? 'dark' : 'light')
    setIsDark(mode === 'dark')
    applyTheme(mode)
  }, [])

  const toggleTheme = () => {
    const next = isDark ? 'light' : 'dark'
    setIsDark(!isDark)
    applyTheme(next)
    if (typeof onThemeToggle === 'function') onThemeToggle(next)
  }

  // Login
  const submit = async (e) => {
    e.preventDefault()
    try {
      const body = new URLSearchParams()
      body.append('username', email)
      body.append('password', password)
      const res = await fetch('/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString()
      })
      if (!res.ok) throw new Error('Invalid credentials')
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      toast.success('Welcome!')
      navigate('/')
      
    } catch (err) {
      toast.error(err.message)
    }
  }

  const fadeUp = useMemo(
    () => ({ initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 } }),
    []
  )

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-50 dark:bg-surface transition-colors duration-300">
      <div aria-hidden className="auth-bg pointer-events-none absolute inset-0 -z-10" />

      <button
        onClick={toggleTheme}
        aria-label="Toggle theme"
        className="absolute right-6 top-6 inline-flex h-10 w-10 items-center justify-center
           rounded-xl bg-white/60 dark:bg-white/5 backdrop-blur-md shadow-card
           hover:bg-white/70 dark:hover:bg-white/10 ring-1 ring-black/10 dark:ring-white/10
           focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60
           transition-colors duration-300"
      >
        {isDark ? <Sun size={18} /> : <Moon size={18} />}
      </button>

      <motion.div
        {...fadeUp}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md rounded-2xl
           bg-white/80 dark:bg-glass/80
           p-8 shadow-card backdrop-blur-xl
           ring-1 ring-black/10 dark:ring-0 ring-offset-0 dark:ring-white/10
           overflow-hidden bg-clip-padding
           transition-colors duration-300"
      >
        <div className="mb-2">
          <div className={`flex items-center gap-3 px-1`}>
            <div className={`flex items-center justify-center h-12 w-12`}
              style={{ filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1)) drop-shadow(0 2px 4px rgba(0, 0, 0, 0.06))'}}
              aria-label="Logo"
            >
              <img src="/logo.svg" alt="Tangled Logo" className="h-full w-full object-contain -ml-1"/>
            </div>
            <div className="flex-1">
              <img src="/tangled-text.svg" alt="Tangled" className="h-5 w-auto mb-0.5"/>
            </div>
          </div>
          <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
            Sign in to continue
          </p>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="relative">
            <CircleUserRound className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 opacity-70" size={18} />
            <input
              type="text"
              autoComplete="email"
              placeholder="Username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="block w-full rounded-xl bg-white/70 dark:bg-white/5
                px-11 py-2 text-sm text-slate-900 dark:text-slate-100
                ring-1 ring-black/10 dark:ring-white/10
                placeholder:text-slate-500 dark:placeholder:text-slate-400
                focus:outline-none focus:ring-2 focus:ring-primary/70
                transition-colors duration-300"
            />
          </div>

          <div className="relative">
            <Lock className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 opacity-70" size={18} />
            <input
              type="password"
              autoComplete="current-password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="block w-full rounded-xl bg-white/70 dark:bg-white/5
                px-11 py-2 text-sm text-slate-900 dark:text-slate-100
                ring-1 ring-black/10 dark:ring-white/10
                placeholder:text-slate-500 dark:placeholder:text-slate-400
                focus:outline-none focus:ring-2 focus:ring-primary/70
                transition-colors duration-300"
            />
          </div>

          <button
            type="submit"
            className="group relative mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary/90 px-4 py-3 text-sm font-medium text-white shadow-lg transition hover:bg-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/60"
          >
            <span>Sign in</span>
            <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </button>
        </form>
      </motion.div>
    </div>
  )
}
