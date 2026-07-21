<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToLogin() {
  router.push('/login')
}

function scrollToSection(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const navLinks = [
  { id: 'features', label: 'Features' },
  { id: 'roles', label: 'Roles' },
  { id: 'about', label: 'About' },
  { id: 'how', label: 'How it works' },
]

const stats = [
  { value: '240', label: 'Flats managed' },
  { value: '4', label: 'Role-based portals' },
  { value: '12k+', label: 'Complaints resolved' },
  { value: '<15m', label: 'Avg alert response' },
]

const features = [
  {
    icon: '✨',
    grad: 'linear-gradient(150deg, #0A4174, #49769F)',
    title: 'AI-triaged complaints',
    body: 'Snap a photo and describe the issue — Niwaas suggests the right category and vendor automatically, so nothing sits in a queue.',
  },
  {
    icon: '📅',
    grad: 'linear-gradient(150deg, #49769F, #78BDE9)',
    title: 'Amenity booking',
    body: 'Reserve the clubhouse, pool or garden in seconds. See live availability instead of calling around to check.',
  },
  {
    icon: '🎫',
    grad: 'linear-gradient(150deg, #001D39, #0A4174)',
    title: 'Visitor gate passes',
    body: 'Pre-register guests with a one-tap gate pass that security can verify instantly at the gate.',
  },
  {
    icon: '🚨',
    grad: 'linear-gradient(150deg, #FF8A6B, #FF5E7A)',
    title: 'Emergency broadcast',
    body: 'One tap reaches every resident and the security desk in seconds, any time of day or night.',
  },
  {
    icon: '💳',
    grad: 'linear-gradient(150deg, #0A4174, #78BDE9)',
    title: 'Maintenance & dues',
    body: 'Track payments, download receipts, and see exactly where society funds are going, always up to date.',
  },
  {
    icon: '🔧',
    grad: 'linear-gradient(150deg, #49769F, #0A4174)',
    title: 'Vendor directory',
    body: 'A trusted, verified list of plumbers, electricians and more — ready the moment a job is assigned.',
  },
]

const roles = [
  {
    icon: '🏠',
    grad: 'linear-gradient(150deg, #80D8E9, #49769F)',
    name: 'Resident',
    desc: 'Raise complaints, book amenities, pre-register visitors and track dues, all from one calm dashboard.',
  },
  {
    icon: '👥',
    grad: 'linear-gradient(150deg, #0A4174, #49769F)',
    name: 'Secretary',
    desc: 'Run the whole society from a single desk — approve bookings, assign vendors, post notices and more.',
  },
  {
    icon: '🛡',
    grad: 'linear-gradient(150deg, #FF8A6B, #FF5E7A)',
    name: 'Security',
    desc: 'Verify gate passes instantly and keep a live log of every visitor checking in and out.',
  },
  {
    icon: '🔧',
    grad: 'linear-gradient(150deg, #49769F, #001D39)',
    name: 'Vendor',
    desc: 'Get notified the moment a job is assigned, with everything you need to get it done right.',
  },
]

const steps = [
  {
    n: '01',
    title: 'Register your flat',
    body: 'Your secretary sends you an invite code. Set your password and you’re straight in.',
  },
  {
    n: '02',
    title: 'Pick your portal',
    body: 'Resident, secretary, security or vendor — everyone gets a dashboard built for exactly their job.',
  },
  {
    n: '03',
    title: 'Run the society',
    body: 'Complaints, bookings, visitors and dues — all tracked, all transparent, all in one place.',
  },
]
</script>

<template>
  <div class="landing">

    <!-- nav -->
    <header class="nav">
      <div class="nav-inner">
        <div class="nav-logo">
          <div class="logo-mark">N</div>
          <span class="logo-name">Niwaas</span>
        </div>
        <nav class="nav-links">
          <a
            v-for="link in navLinks"
            :key="link.id"
            :href="`#${link.id}`"
            @click.prevent="scrollToSection(link.id)"
          >{{ link.label }}</a>
        </nav>
        <button class="btn-login" @click="goToLogin">Login →</button>
      </div>
    </header>

    <!-- hero -->
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-left">
          <div class="hero-pill"><span class="pill-dot"></span>Raghvendra Sai Society · Hyderabad</div>
          <h1 class="hero-title">Your society,<br><span class="hero-title-accent">running itself.</span></h1>
          <p class="hero-desc">Complaints, amenities, visitors, dues and emergencies — one calm, beautiful platform for residents, secretary, security and vendors.</p>
          <p class="hero-tagline">"Dial a Secretary… Not Anymore."</p>
          <div class="hero-actions">
            <button class="btn-cta" @click="goToLogin">Get started →</button>
            <a href="#roles" class="btn-outline" @click.prevent="scrollToSection('roles')">Explore roles</a>
          </div>
        </div>

        <!-- glass mockup -->
        <div class="hero-right">
          <div class="mockup-card">
            <div class="mockup-topbar">
              <span class="dot" style="background:#FF8A6B"></span>
              <span class="dot" style="background:#F5C243"></span>
              <span class="dot" style="background:#80D8E9"></span>
              <span class="mockup-label">Resident · A-402</span>
            </div>
            <div class="mockup-stats">
              <div class="mockup-stat">
                <div class="mockup-stat-label">Open complaints</div>
                <div class="mockup-stat-value">2</div>
              </div>
              <div class="mockup-stat">
                <div class="mockup-stat-label">Pending dues</div>
                <div class="mockup-stat-value">₹13,250</div>
              </div>
            </div>
            <div class="mockup-list">
              <div class="mockup-row mockup-row-border">
                <span class="mockup-icon" style="background:linear-gradient(150deg,#FF8A6B,#FF5E7A)">⚠</span>
                <div class="mockup-row-body">
                  <div class="mockup-row-title">CMP-2043 · Plumbing</div>
                  <div class="mockup-row-sub">Kitchen sink leak</div>
                </div>
                <span class="mockup-chip mockup-chip-warm">In Progress</span>
              </div>
              <div class="mockup-row">
                <span class="mockup-icon" style="background:linear-gradient(150deg,#49769F,#80D8E9)">📅</span>
                <div class="mockup-row-body">
                  <div class="mockup-row-title">Clubhouse booking</div>
                  <div class="mockup-row-sub">4 Jul · 6–9 PM</div>
                </div>
                <span class="mockup-chip mockup-chip-cool">Confirmed</span>
              </div>
            </div>
          </div>

          <div class="badge-float badge-top">
            <span class="badge-icon">✨</span>AI suggested: Plumbing
          </div>
          <div class="badge-float badge-bottom">
            <span class="badge-check">✓</span>
            <div>
              <div class="badge-code">GATE-7712</div>
              <div class="badge-sub">Visitor verified</div>
            </div>
          </div>
        </div>
      </div>

      <!-- stats bar -->
      <div class="stats-bar">
        <div class="stats-inner">
          <div v-for="s in stats" :key="s.label" class="stat-item">
            <div class="stat-value">{{ s.value }}</div>
            <div class="stat-label">{{ s.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- features -->
    <section id="features" class="features-section">
      <div class="section-inner">
        <div class="section-head">
          <div class="eyebrow">Everything in one place</div>
          <h2 class="section-title">One platform. Every society task.</h2>
          <p class="section-sub">From a leaking tap to a fire drill, Niwaas gives every resident and manager exactly the right tools — beautifully organised.</p>
        </div>
        <div class="features-grid">
          <div v-for="f in features" :key="f.title" class="feature-card">
            <div class="feature-icon" :style="{ background: f.grad }">{{ f.icon }}</div>
            <div class="feature-title">{{ f.title }}</div>
            <div class="feature-body">{{ f.body }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- roles -->
    <section id="roles" class="roles-section">
      <div class="section-inner">
        <div class="section-head">
          <div class="eyebrow eyebrow-light">Built for everyone at the gate & beyond</div>
          <h2 class="section-title section-title-light">Four portals, one society</h2>
          <p class="section-sub section-sub-light">Every role gets a focused dashboard — no clutter, no guesswork. Pick yours to jump straight in.</p>
        </div>
        <div class="roles-grid">
          <div v-for="r in roles" :key="r.name" class="role-card">
            <div class="role-icon" :style="{ background: r.grad }">{{ r.icon }}</div>
            <div class="role-name">{{ r.name }}</div>
            <div class="role-desc">{{ r.desc }}</div>
            <button class="btn-role" @click="goToLogin">Enter as {{ r.name }} →</button>
          </div>
        </div>
      </div>
    </section>

    <!-- about -->
    <section id="about" class="about-section">
      <div class="about-inner">
        <div class="about-text">
          <div class="eyebrow">About Niwaas</div>
          <h2 class="about-title">Less WhatsApp chaos. More community.</h2>
          <p class="about-p">Niwaas was built for Raghvendra Sai Society to replace endless secretary phone calls and scattered group messages with one shared, transparent system. Every complaint, booking, visitor and payment lives in one trail everyone can trust.</p>
          <p class="about-p">Residents raise and track issues in seconds, the committee manages the whole society from a single desk, security verifies visitors instantly, and vendors know exactly what needs doing.</p>
          <div class="about-checklist">
            <div class="check-item"><span class="check-icon">✓</span>Transparent, tamper-proof records for the whole society</div>
            <div class="check-item"><span class="check-icon">✓</span>AI that routes complaints to the right vendor, faster</div>
            <div class="check-item"><span class="check-icon">✓</span>Emergency alerts that reach the gate in seconds</div>
          </div>
        </div>
        <div class="about-side">
          <div class="quote-card">
            <div class="quote-mark">"</div>
            <div class="quote-text">Committee work that used to eat my evenings now takes ten minutes a day. The residents finally feel heard.</div>
            <div class="quote-author">
              <div class="quote-avatar">PN</div>
              <div>
                <div class="quote-name">Priya Nair</div>
                <div class="quote-role">Hon. Secretary</div>
              </div>
            </div>
          </div>
          <div class="about-stats">
            <div class="about-stat-card">
              <div class="about-stat-value">92%</div>
              <div class="about-stat-label">complaints resolved on time</div>
            </div>
            <div class="about-stat-card">
              <div class="about-stat-value">4.8★</div>
              <div class="about-stat-label">average resident rating</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- how it works -->
    <section id="how" class="how-section">
      <div class="section-inner">
        <div class="section-head">
          <div class="eyebrow">How it works</div>
          <h2 class="section-title">Up and running in three steps</h2>
        </div>
        <div class="steps-grid">
          <div v-for="s in steps" :key="s.n" class="step-card">
            <div class="step-num">{{ s.n }}</div>
            <div class="step-title">{{ s.title }}</div>
            <div class="step-body">{{ s.body }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="cta-card">
        <h2 class="cta-title">Ready to let your society run itself?</h2>
        <p class="cta-sub">Sign in to your portal and see how calm society management can feel.</p>
        <button class="btn-cta btn-cta-lg" @click="goToLogin">Get started →</button>
      </div>
    </section>

    <!-- footer -->
    <footer class="site-footer">
      <div class="footer-grid">
        <div class="footer-brand">
          <div class="footer-logo">
            <div class="logo-mark">N</div>
            <span class="footer-logo-name">Niwaas</span>
          </div>
          <div class="footer-tagline">Society OS for Raghvendra Sai Society, Hyderabad. Dial a Secretary… Not Anymore.</div>
        </div>
        <div class="footer-col">
          <div class="footer-col-title">Product</div>
          <a href="#features" @click.prevent="scrollToSection('features')">Features</a>
          <a href="#roles" @click.prevent="scrollToSection('roles')">Roles</a>
          <a href="#how" @click.prevent="scrollToSection('how')">How it works</a>
        </div>
        <div class="footer-col">
          <div class="footer-col-title">Society</div>
          <a href="#about" @click.prevent="scrollToSection('about')">About</a>
          <span>Committee</span>
          <span>Contact</span>
        </div>
        <div class="footer-col">
          <div class="footer-col-title">Get started</div>
          <button class="footer-login-btn" @click="goToLogin">Login →</button>
        </div>
      </div>
      <div class="footer-bottom">
        <div>© 2026 Niwaas · Trusted by 240 flats</div>
        <div>Made with care in Hyderabad</div>
      </div>
    </footer>

  </div>
</template>

<style scoped>
.landing {
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
  background: #fff;
  color: #0F2942;
  min-height: 100vh;
}

/* ── nav ── */
.nav {
  position: sticky;
  top: 0;
  z-index: 40;
  backdrop-filter: blur(14px);
  background: rgba(0, 29, 57, 0.8);
  border-bottom: 1px solid rgba(255, 255, 255, 0.09);
}

.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 15px 26px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.nav-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.logo-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(150deg, #80D8E9, #49769F);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #001D39;
  font-weight: 800;
  font-size: 18px;
  flex-shrink: 0;
}

.logo-name {
  color: #fff;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 30px;
}

.nav-links a {
  color: #C7D9E8;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: color 0.15s ease;
}

.nav-links a:hover { color: #80D8E9; }

.btn-login {
  background: linear-gradient(150deg, #FF8A6B, #FF5E7A);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  padding: 10px 20px;
  border-radius: 11px;
  box-shadow: 0 8px 20px rgba(255, 94, 122, 0.35);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
  white-space: nowrap;
}

.btn-login:hover {
  box-shadow: 0 10px 26px rgba(255, 94, 122, 0.5);
  transform: translateY(-1px);
}

/* ── hero ── */
.hero {
  position: relative;
  overflow: hidden;
  color: #fff;
  background:
    radial-gradient(1100px 640px at 82% -8%, rgba(120, 189, 233, 0.4), transparent 60%),
    radial-gradient(760px 520px at 4% 16%, rgba(255, 122, 107, 0.24), transparent 55%),
    linear-gradient(165deg, #001325, #03294c 58%, #0A4174);
}

.hero-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 74px 26px 88px;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 46px;
  align-items: center;
  position: relative;
}

.hero-left { animation: niwRise 0.6s ease both; }

.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 7px 15px;
  border-radius: 999px;
  background: rgba(128, 216, 233, 0.14);
  border: 1px solid rgba(128, 216, 233, 0.3);
  font-size: 12.5px;
  font-weight: 700;
  color: #BEEAF5;
  margin-bottom: 24px;
}

.pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #80D8E9;
}

.hero-title {
  font-size: 56px;
  line-height: 1.04;
  font-weight: 800;
  letter-spacing: -1.8px;
  margin: 0 0 20px;
}

.hero-title-accent {
  background: linear-gradient(100deg, #80D8E9, #FF9A8A);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 18px;
  line-height: 1.55;
  color: #BBD2E4;
  max-width: 490px;
  margin: 0 0 10px;
}

.hero-tagline {
  font-size: 16px;
  font-style: italic;
  color: #80D8E9;
  font-weight: 600;
  margin: 0 0 30px;
}

.hero-actions {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.btn-cta {
  background: linear-gradient(150deg, #FF8A6B, #FF5E7A);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  padding: 15px 28px;
  border-radius: 13px;
  box-shadow: 0 14px 34px rgba(255, 94, 122, 0.42);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.btn-cta:hover {
  box-shadow: 0 18px 40px rgba(255, 94, 122, 0.55);
  transform: translateY(-1px);
}

.btn-cta-lg {
  font-size: 16px;
  font-weight: 800;
  padding: 16px 34px;
  border-radius: 14px;
}

.btn-outline {
  text-decoration: none;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  padding: 15px 26px;
  border-radius: 13px;
  display: inline-flex;
  align-items: center;
  transition: background 0.15s ease;
}

.btn-outline:hover { background: rgba(255, 255, 255, 0.18); }

/* glass mockup */
.hero-right {
  position: relative;
  animation: niwRise 0.85s ease both;
}

.mockup-card {
  background: rgba(255, 255, 255, 0.09);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 24px;
  padding: 20px;
  box-shadow: 0 44px 90px rgba(0, 0, 0, 0.45);
}

.mockup-topbar {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 16px;
}

.dot { width: 11px; height: 11px; border-radius: 50%; }

.mockup-label {
  margin-left: auto;
  font-size: 11px;
  color: #9FBBD2;
  font-weight: 600;
}

.mockup-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
  margin-bottom: 11px;
}

.mockup-stat {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  padding: 14px;
}

.mockup-stat-label { font-size: 11px; color: #9FBBD2; font-weight: 600; }
.mockup-stat-value { font-size: 26px; font-weight: 800; margin-top: 5px; }

.mockup-list {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 14px;
  padding: 13px 15px;
}

.mockup-row {
  display: flex;
  align-items: center;
  gap: 11px;
  padding-top: 11px;
}

.mockup-row-border {
  padding-top: 0;
  padding-bottom: 11px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.mockup-icon {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  font-size: 14px;
}

.mockup-row-body { flex: 1; min-width: 0; }
.mockup-row-title { font-size: 12.5px; font-weight: 700; }
.mockup-row-sub { font-size: 11px; color: #9FBBD2; }

.mockup-chip {
  font-size: 10.5px;
  font-weight: 700;
  padding: 4px 9px;
  border-radius: 999px;
  flex-shrink: 0;
}

.mockup-chip-warm { color: #FFD9C7; background: rgba(255, 138, 107, 0.22); }
.mockup-chip-cool { color: #BEEAF5; background: rgba(128, 216, 233, 0.2); }

.badge-float {
  position: absolute;
  background: #fff;
  color: #0A4174;
  border-radius: 13px;
  padding: 11px 14px;
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.25);
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 800;
}

.badge-top {
  top: -18px;
  right: -14px;
  animation: niwFloat 4s ease-in-out infinite;
}

.badge-bottom {
  bottom: -20px;
  left: -16px;
  animation: niwFloat 5s ease-in-out 0.6s infinite;
}

.badge-icon { display: flex; }

.badge-check {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #DDF3E7;
  color: #1E7A50;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.badge-code { font-size: 12px; font-weight: 800; color: #001D39; font-family: ui-monospace, monospace; }
.badge-sub { font-size: 10.5px; color: #1E7A50; font-weight: 700; }

/* stats bar */
.stats-bar {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  position: relative;
}

.stats-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 26px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-value {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.6px;
  background: linear-gradient(100deg, #80D8E9, #78BDE9);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.stat-label { font-size: 13px; color: #9FBBD2; margin-top: 2px; }

/* ── shared section styles ── */
.section-inner { max-width: 1200px; margin: 0 auto; }

.section-head {
  text-align: center;
  max-width: 660px;
  margin: 0 auto 54px;
}

.eyebrow {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: #4E8EA2;
  margin-bottom: 12px;
}

.eyebrow-light { color: #80D8E9; }

.section-title {
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -1.2px;
  color: #001D39;
  margin: 0 0 14px;
}

.section-title-light { color: #fff; }

.section-sub {
  font-size: 17px;
  color: #5A768C;
  line-height: 1.55;
  margin: 0;
}

.section-sub-light { color: #AEC6DA; }

/* ── features ── */
.features-section {
  background: #fff;
  padding: 90px 26px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(330px, 1fr));
  gap: 22px;
}

.feature-card {
  background: #fff;
  border: 1px solid #E7EDF3;
  border-radius: 18px;
  padding: 26px;
  box-shadow: 0 2px 10px rgba(10, 65, 116, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.feature-card:hover {
  border-color: #D6E4F0;
  box-shadow: 0 18px 40px rgba(10, 65, 116, 0.14);
  transform: translateY(-4px);
}

.feature-icon {
  width: 54px;
  height: 54px;
  border-radius: 15px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 17px;
  box-shadow: 0 12px 26px rgba(10, 65, 116, 0.2);
  font-size: 22px;
}

.feature-title { font-size: 18px; font-weight: 800; color: #001D39; margin-bottom: 8px; }
.feature-body { font-size: 14.5px; color: #5A768C; line-height: 1.6; }

/* ── roles ── */
.roles-section {
  background:
    radial-gradient(900px 500px at 90% 0%, rgba(120, 189, 233, 0.22), transparent 60%),
    linear-gradient(165deg, #001D39, #0A4174);
  padding: 90px 26px;
  color: #fff;
}

.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(258px, 1fr));
  gap: 20px;
}

.role-card {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 20px;
  padding: 24px;
  backdrop-filter: blur(8px);
}

.role-icon {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.25);
  font-size: 21px;
}

.role-name { font-size: 19px; font-weight: 800; margin-bottom: 7px; }
.role-desc { font-size: 14px; color: #AEC6DA; line-height: 1.55; margin-bottom: 18px; min-height: 63px; }

.btn-role {
  width: 100%;
  padding: 11px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 13.5px;
  font-weight: 700;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.btn-role:hover {
  background: #80D8E9;
  border-color: #80D8E9;
  color: #001D39;
}

/* ── about ── */
.about-section {
  background: #F4F9FC;
  padding: 90px 26px;
}

.about-inner {
  max-width: 1160px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 52px;
  align-items: center;
}

.about-title {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -1.1px;
  color: #001D39;
  margin: 0 0 18px;
  line-height: 1.12;
}

.about-p {
  font-size: 16px;
  color: #5A768C;
  line-height: 1.65;
  margin: 0 0 16px;
}

.about-checklist {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 22px;
}

.check-item {
  display: flex;
  align-items: center;
  gap: 11px;
  font-size: 14.5px;
  color: #12314C;
  font-weight: 600;
}

.check-icon {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #DDF3E7;
  color: #1E7A50;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 13px;
}

.about-side {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.quote-card {
  background: linear-gradient(150deg, #0A4174, #49769F);
  border-radius: 20px;
  padding: 26px;
  color: #fff;
  box-shadow: 0 20px 44px rgba(10, 65, 116, 0.2);
}

.quote-mark { font-size: 30px; line-height: 1; color: #80D8E9; font-weight: 800; }
.quote-text { font-size: 16px; line-height: 1.55; font-weight: 600; margin: 6px 0 16px; }

.quote-author { display: flex; align-items: center; gap: 11px; }

.quote-avatar {
  width: 40px;
  height: 40px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 14px;
  flex-shrink: 0;
}

.quote-name { font-size: 14px; font-weight: 700; }
.quote-role { font-size: 12px; color: #BEEAF5; }

.about-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.about-stat-card {
  background: #fff;
  border: 1px solid #E7EDF3;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(10, 65, 116, 0.05);
}

.about-stat-value { font-size: 32px; font-weight: 800; color: #001D39; letter-spacing: -0.6px; }
.about-stat-label { font-size: 13px; color: #5A768C; margin-top: 3px; }

/* ── how it works ── */
.how-section {
  background: #fff;
  padding: 90px 26px;
}

.how-section .section-inner { max-width: 1100px; }

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 22px;
}

.step-card {
  background: #F4F9FC;
  border: 1px solid #E7EDF3;
  border-radius: 20px;
  padding: 28px;
}

.step-num {
  font-size: 34px;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(120deg, #49769F, #FF8A6B);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 12px;
}

.step-title { font-size: 19px; font-weight: 800; color: #001D39; margin-bottom: 8px; }
.step-body { font-size: 14.5px; color: #5A768C; line-height: 1.6; }

/* ── CTA ── */
.cta-section {
  padding: 8px 26px 84px;
  background: #fff;
}

.cta-card {
  max-width: 1080px;
  margin: 0 auto;
  border-radius: 28px;
  padding: 60px 40px;
  text-align: center;
  color: #fff;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(720px 420px at 12% 18%, rgba(255, 122, 107, 0.4), transparent 58%),
    radial-gradient(680px 420px at 92% 90%, rgba(120, 189, 233, 0.32), transparent 60%),
    linear-gradient(150deg, #0A4174, #001D39);
  box-shadow: 0 30px 70px rgba(0, 29, 57, 0.28);
}

.cta-title { font-size: 40px; font-weight: 800; letter-spacing: -1.2px; margin: 0 0 14px; }
.cta-sub {
  font-size: 17px;
  color: #C7DBEC;
  margin: 0 auto 28px;
  max-width: 520px;
  line-height: 1.55;
}

/* ── footer ── */
.site-footer {
  background: #001D39;
  color: #8FA8BF;
  padding: 52px 26px 30px;
}

.footer-grid {
  max-width: 1160px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.6fr 1fr 1fr 1fr;
  gap: 32px;
}

.footer-logo {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-bottom: 14px;
}

.footer-logo .logo-mark { width: 38px; height: 38px; border-radius: 11px; }
.footer-logo-name { color: #fff; font-size: 18px; font-weight: 800; }

.footer-tagline { font-size: 13.5px; line-height: 1.6; max-width: 280px; }

.footer-col-title { color: #fff; font-size: 13px; font-weight: 700; margin-bottom: 12px; }

.footer-col {
  display: flex;
  flex-direction: column;
  gap: 9px;
  font-size: 13.5px;
}

.footer-col a { color: #8FA8BF; text-decoration: none; }
.footer-col a:hover { color: #80D8E9; }

.footer-login-btn {
  color: #80D8E9;
  font-weight: 700;
  text-align: left;
  font-size: 13.5px;
}

.footer-bottom {
  max-width: 1160px;
  margin: 32px auto 0;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12.5px;
}

/* ── animations ── */
@keyframes niwFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-13px); }
}

@keyframes niwRise {
  0% { opacity: 0; transform: translateY(26px); }
  100% { opacity: 1; transform: translateY(0); }
}

/* ── responsive ── */
@media (max-width: 880px) {
  .hero-inner { grid-template-columns: 1fr; }
  .about-inner { grid-template-columns: 1fr; }
  .footer-grid { grid-template-columns: 1fr 1fr; }
  .nav-links { display: none; }
  .badge-float { display: none; }
  .stats-inner { grid-template-columns: 1fr 1fr; }
}
</style>


