'use client'

import { Bell, Bot, CreditCard, Lock, Palette, Shield } from 'lucide-react'

const sections = [
  {
    icon: Bot,
    title: 'Bot settings',
    description: 'Bot name, texts, maintenance mode, and auto-delivery',
  },
  {
    icon: CreditCard,
    title: 'Payment methods',
    description: 'Payment providers and base currency',
  },
  {
    icon: Bell,
    title: 'Notifications',
    description: 'Admin alerts and store events',
  },
  {
    icon: Shield,
    title: 'Security',
    description: 'Password, sessions, and activity log',
  },
  {
    icon: Palette,
    title: 'Interface',
    description: 'Dashboard language and time zone',
  },
]

export default function SettingsTab() {
  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">This section is temporarily locked for changes</p>
      </div>

      <div className="rounded-2xl bg-card border border-border p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-neon/10 border border-neon/20 flex items-center justify-center shrink-0">
            <Lock className="w-5 h-5 text-neon" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Settings are not wired yet</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Settings management is intentionally left without fake values or inactive controls. The rest of the dashboard already works through the project API.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-3">
        {sections.map((section) => {
          const Icon = section.icon
          return (
            <div key={section.title} className="rounded-2xl bg-card border border-border p-5 opacity-70">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-white/5 border border-border flex items-center justify-center">
                  <Icon className="w-4 h-4 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground">{section.title}</h3>
                  <p className="text-xs text-muted-foreground">{section.description}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
