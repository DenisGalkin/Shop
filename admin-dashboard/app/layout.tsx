import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import RegisterSW from '@/components/pwa/RegisterSW'
import './globals.css'

const inter = Inter({ subsets: ['latin', 'cyrillic'] })
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: 'VEXND SHOP Admin',
  description: 'Administrative dashboard for the VEXND SHOP digital goods bot',
  generator: 'v0.app',
  manifest: '/admin/manifest.webmanifest',
  icons: {
    icon: [
      { url: '/admin/icon-light-32x32.png', sizes: '32x32', media: '(prefers-color-scheme: light)' },
      { url: '/admin/icon-dark-32x32.png', sizes: '32x32', media: '(prefers-color-scheme: dark)' },
      { url: '/admin/icon-192.png', sizes: '192x192', type: 'image/png' },
    ],
    apple: [{ url: '/admin/apple-icon.png', sizes: '180x180' }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'VEXND Admin',
  },
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0a0c14',
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className={`${inter.className} ${jetbrainsMono.variable} antialiased`}>
        {children}
        <RegisterSW />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
