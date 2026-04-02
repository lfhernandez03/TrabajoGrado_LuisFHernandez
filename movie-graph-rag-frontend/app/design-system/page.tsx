'use client'

import { COLORS } from '@/lib/utils'

export default function DesignSystem() {
  return (
    <div className="min-h-screen bg-bg text-text p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-16">
          <h1 className="font-display text-6xl mb-4">
            <span className="text-text">CineGraph</span>{' '}
            <span className="text-accent">Design System</span>
          </h1>
          <p className="text-muted text-lg">
            Design tokens and component reference for the CineGraph frontend.
          </p>
        </div>

        {/* Color Palette */}
        <section className="mb-16">
          <h2 className="font-display text-4xl mb-8">Color Palette</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* BG */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-bg border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">bg</h3>
                <p className="text-muted text-sm">#080a0f</p>
                <p className="text-muted text-xs">Background total</p>
              </div>
            </div>

            {/* Surface */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-surface border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">surface</h3>
                <p className="text-muted text-sm">#0f1117</p>
                <p className="text-muted text-xs">Cards, panels, navbar</p>
              </div>
            </div>

            {/* Surface2 */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-surface2 border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">surface2</h3>
                <p className="text-muted text-sm">#161b26</p>
                <p className="text-muted text-xs">Elevated surfaces, inputs</p>
              </div>
            </div>

            {/* Text */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-text border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">text</h3>
                <p className="text-muted text-sm">#f0ece4</p>
                <p className="text-muted text-xs">Primary text</p>
              </div>
            </div>

            {/* Muted */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-muted border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">muted</h3>
                <p className="text-muted text-sm">#7a7870</p>
                <p className="text-muted text-xs">Secondary text, placeholders</p>
              </div>
            </div>

            {/* Accent */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-accent border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">accent</h3>
                <p className="text-muted text-sm">#e8a040</p>
                <p className="text-muted text-xs">Primary action, logo GRAPH</p>
              </div>
            </div>

            {/* Accent2 */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-accent2 border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">accent2</h3>
                <p className="text-muted text-sm">#c95f3a</p>
                <p className="text-muted text-xs">CTA buttons, primary buttons</p>
              </div>
            </div>

            {/* Teal */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-teal border border-border rounded-lg"></div>
              <div>
                <h3 className="font-semibold">teal</h3>
                <p className="text-muted text-sm">#2ec4a6</p>
                <p className="text-muted text-xs">Semantic, scores, badges</p>
              </div>
            </div>

            {/* Border */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-surface border-2 border-border rounded-lg flex items-center justify-center">
                <p className="text-muted text-sm">rgba(255,255,255,0.07)</p>
              </div>
              <div>
                <h3 className="font-semibold">border</h3>
                <p className="text-muted text-xs">Subtle border</p>
              </div>
            </div>

            {/* Border2 */}
            <div className="space-y-3">
              <div className="w-full h-32 bg-surface border-2 border-border2 rounded-lg flex items-center justify-center">
                <p className="text-muted text-sm">rgba(255,255,255,0.13)</p>
              </div>
              <div>
                <h3 className="font-semibold">border2</h3>
                <p className="text-muted text-xs">Elevated border</p>
              </div>
            </div>
          </div>
        </section>

        {/* Typography */}
        <section className="mb-16">
          <h2 className="font-display text-4xl mb-8">Typography</h2>
          <div className="space-y-8">
            <div>
              <h1 className="text-5xl font-bold mb-2">Bebas Neue Display — H1</h1>
              <p className="text-muted">Letters: 0.02em spacing | 60px</p>
            </div>
            <div>
              <h2 className="font-display text-4xl font-bold mb-2">Bebas Neue Display — H2</h2>
              <p className="text-muted">48px</p>
            </div>
            <div>
              <h3 className="font-body text-2xl font-semibold mb-2">DM Sans Body — H3</h3>
              <p className="text-muted">28px, Semi Bold</p>
            </div>
            <div>
              <p className="font-body text-base mb-2">DM Sans Body — Regular paragraph text</p>
              <p className="text-muted">16px, 400 weight | Line height 1.6</p>
            </div>
            <div>
              <p className="font-body text-sm text-muted mb-2">DM Sans Body — Secondary/Muted text</p>
              <p className="text-muted">14px, Muted color</p>
            </div>
          </div>
        </section>

        {/* Animations */}
        <section className="mb-16">
          <h2 className="font-display text-4xl mb-8">Animations</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* pulse-dot */}
            <div className="bg-surface p-6 rounded-lg border border-border">
              <div className="flex items-center justify-center gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-teal animate-pulse-dot"></div>
                <div className="w-3 h-3 rounded-full bg-teal animate-pulse-dot" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-3 h-3 rounded-full bg-teal animate-pulse-dot" style={{ animationDelay: '0.4s' }}></div>
              </div>
              <h3 className="font-semibold mb-1">pulse-dot</h3>
              <p className="text-muted text-sm">2s ease-in-out infinite</p>
              <p className="text-muted text-xs mt-2">Use: Loading indicators, live status</p>
            </div>

            {/* fade-in */}
            <div className="bg-surface p-6 rounded-lg border border-border">
              <div className="text-3xl animate-fade-in mb-4">✨</div>
              <h3 className="font-semibold mb-1">fade-in</h3>
              <p className="text-muted text-sm">0.3s ease-out</p>
              <p className="text-muted text-xs mt-2">Use: Element appearance, modal open</p>
            </div>

            {/* slide-up */}
            <div className="bg-surface p-6 rounded-lg border border-border">
              <div className="text-3xl animate-slide-up mb-4">⬆️</div>
              <h3 className="font-semibold mb-1">slide-up</h3>
              <p className="text-muted text-sm">0.4s cubic-bezier(0.34, 1.56, 0.64, 1)</p>
              <p className="text-muted text-xs mt-2">Use: Content entering, transitions</p>
            </div>

            {/* fill-bar */}
            <div className="bg-surface p-6 rounded-lg border border-border">
              <div className="w-full bg-surface2 h-2 rounded-full overflow-hidden mb-4">
                <div
                  className="h-full bg-teal animate-fill-bar"
                  style={{ '--fill-width': '100%' } as React.CSSProperties}
                ></div>
              </div>
              <h3 className="font-semibold mb-1">fill-bar</h3>
              <p className="text-muted text-sm">0.6s ease-out forwards</p>
              <p className="text-muted text-xs mt-2">Use: ScoreBar, progress indicators</p>
            </div>
          </div>
        </section>

        {/* Components Demo */}
        <section className="mb-16">
          <h2 className="font-display text-4xl mb-8">Component Examples</h2>
          <div className="space-y-8">
            {/* Button Examples */}
            <div>
              <h3 className="font-semibold mb-4">Buttons</h3>
              <div className="flex flex-wrap gap-4">
                <button className="bg-accent2 text-bg px-6 py-2 rounded hover:opacity-90 transition">
                  Primary CTA
                </button>
                <button className="bg-teal text-bg px-6 py-2 rounded hover:opacity-90 transition">
                  Secondary
                </button>
                <button className="bg-surface2 text-text border border-border px-6 py-2 rounded hover:bg-border transition">
                  Ghost
                </button>
              </div>
            </div>

            {/* Input Examples */}
            <div>
              <h3 className="font-semibold mb-4">Inputs</h3>
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Search..."
                  className="w-full px-4 py-2 bg-surface2 text-text placeholder:text-muted border border-border rounded"
                />
              </div>
            </div>

            {/* Badge Examples */}
            <div>
              <h3 className="font-semibold mb-4">Badges</h3>
              <div className="flex flex-wrap gap-3">
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-teal/10 text-teal border border-teal/30 text-sm">
                  ● Active
                </span>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-accent/10 text-accent border border-accent/30 text-sm">
                  ● Accent
                </span>
                <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-surface2 text-muted border border-border text-sm">
                  ● Muted
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Common Patterns */}
        <section>
          <h2 className="font-display text-4xl mb-8">Common Patterns</h2>
          <div className="bg-surface border border-border rounded-lg p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center">
                <span className="text-accent text-lg">●</span>
              </div>
              <div className="flex-1">
                <p className="text-text font-semibold">Pattern: Recommendation Badge</p>
                <p className="text-muted text-sm">Use accent or teal with dot indicator for active states</p>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div className="mt-16 pt-8 border-t border-border text-center text-muted">
          <p className="text-sm">CineGraph Design System — Phase 0 Configuration</p>
          <p className="text-xs mt-2">Last updated: {new Date().toLocaleDateString()}</p>
        </div>
      </div>
    </div>
  )
}
