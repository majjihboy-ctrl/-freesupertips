import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import DailyPredictions from './components/DailyPredictions';
import TipCategoryGrid from './components/TipCategoryGrid';
import RecentResults from './components/RecentResults';
import BlogPreview from './components/BlogPreview';
import SEOContent from './components/SEOContent';
import FAQSection from './components/FAQSection';
import Footer from './components/Footer';
import AuthModal from './components/AuthModal';
import AdminDashboard from './components/AdminDashboard';
import Pricing from './components/Pricing';
import DayPage from './components/DayPage';
import TipCategoryPage from './components/TipCategoryPage';
import { useAuth } from './hooks/useAuth';
import { usePremium } from './hooks/usePremium';

function App() {
  const auth = useAuth();
  const { hasPremium } = usePremium(auth.user?.id ?? null);

  return (
    <div className="min-h-screen bg-bg-base text-white antialiased overflow-x-hidden">
      <Navbar
        user={auth.user}
        hasPremium={hasPremium}
        onLogout={auth.handleLogout}
        onOpenAuth={(mode: 'login' | 'signup') => {
          auth.setAuthMode(mode);
          auth.setShowAuthModal(true);
        }}
      />
      <main>
        <Routes>
          <Route path="/" element={
            <>
              <Hero />
              <DailyPredictions />
              <TipCategoryGrid />
              <RecentResults />
              <BlogPreview />
              <SEOContent />
              <FAQSection />
            </>
          } />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/admin" element={<AdminDashboard user={auth.user} />} />
          <Route path="/day/:day" element={<DayPage />} />
          <Route path="/tips/:category" element={<TipCategoryPage />} />
        </Routes>
      </main>
      <Footer />

      <AuthModal
        isOpen={auth.showAuthModal}
        onClose={() => auth.setShowAuthModal(false)}
        authMode={auth.authMode}
        setAuthMode={auth.setAuthMode}
        email={auth.email}
        setEmail={auth.setEmail}
        password={auth.password}
        setPassword={auth.setPassword}
        authError={auth.authError}
        onSubmit={auth.handleLogin}
      />
    </div>
  );
}

export default App;