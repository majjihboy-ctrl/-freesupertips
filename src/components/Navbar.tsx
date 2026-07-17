import { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Navbar() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? 'bg-white shadow-lg' : 'bg-white/95 backdrop-blur-sm'}`}>
      {/* Top Utility Bar */}
      <div className="bg-gray-50 border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-end py-2 text-sm">
            <a href="/tips-store" className="text-gray-600 hover:text-primary mx-3 transition-colors">Tips Store</a>
            <a href="/about" className="text-gray-600 hover:text-primary mx-3 transition-colors">About Us</a>
            <a href="/blog" className="text-gray-600 hover:text-primary mx-3 transition-colors">Blog</a>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center">
            <div className="text-2xl font-bold text-primary">BetMaster</div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link to="/" className="text-gray-700 hover:text-primary font-medium transition-colors">Pool Fixtures</Link>
            <Link to="/blog" className="text-gray-700 hover:text-primary font-medium transition-colors">Blog</Link>
            <button className="px-6 py-2 rounded-full border-2 border-primary text-primary font-semibold hover:bg-primary hover:text-white transition-all">
              Register
            </button>
            <button className="px-6 py-2 rounded-full bg-primary text-white font-semibold hover:bg-primary-hover transition-all">
              Login
            </button>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 text-gray-700"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-gray-200 bg-white">
            <div className="flex flex-col space-y-4 px-4">
              <Link to="/" className="text-gray-700 hover:text-primary font-medium" onClick={() => setMobileMenuOpen(false)}>Pool Fixtures</Link>
              <Link to="/blog" className="text-gray-700 hover:text-primary font-medium" onClick={() => setMobileMenuOpen(false)}>Blog</Link>
              <button className="w-full px-6 py-2 rounded-full border-2 border-primary text-primary font-semibold">Register</button>
              <button className="w-full px-6 py-2 rounded-full bg-primary text-white font-semibold">Login</button>
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}