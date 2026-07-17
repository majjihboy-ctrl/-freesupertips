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

function App() {
  return (
    <div className="min-h-screen bg-white text-gray-900 antialiased overflow-x-hidden">
      <Navbar />
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
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;