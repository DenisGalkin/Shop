'use client'

import { Bell, Bot, CreditCard, Lock, Palette, Shield } from 'lucide-react'

const sections = [
  {
    icon: Bot,
    title: 'Настройки бота',
    description: 'Имя, тексты, режим обслуживания и авто-доставка',
  },
  {
    icon: CreditCard,
    title: 'Платежные методы',
    description: 'Провайдеры оплаты и базовая валюта',
  },
  {
    icon: Bell,
    title: 'Уведомления',
    description: 'Алерты администратора и события магазина',
  },
  {
    icon: Shield,
    title: 'Безопасность',
    description: 'Пароль, сессии и журнал действий',
  },
  {
    icon: Palette,
    title: 'Интерфейс',
    description: 'Язык и часовой пояс панели',
  },
]

export default function SettingsTab() {
  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Настройки</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Раздел временно закрыт для изменений</p>
      </div>

      <div className="rounded-2xl bg-card border border-border p-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-neon/10 border border-neon/20 flex items-center justify-center shrink-0">
            <Lock className="w-5 h-5 text-neon" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-foreground">Настройки пока не подключены</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Управление настройками оставлено без активных кнопок и фальшивых значений. Остальные разделы панели работают через API проекта.
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
