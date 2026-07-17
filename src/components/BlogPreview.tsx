import { Link } from 'react-router-dom';

const blogPosts = [
  { id: 1, title: 'How to Build a Winning Accumulator Strategy', excerpt: 'Learn the secrets to building profitable multi-bet accumulators with our expert guide...', category: 'Strategy' },
  { id: 2, title: 'Understanding Football Statistics for Better Predictions', excerpt: 'Deep dive into the key metrics that matter when analyzing team performance...', category: 'Analysis' },
  { id: 3, title: 'Top 5 Leagues for Consistent Betting Profits', excerpt: 'Discover which leagues offer the best value and most predictable outcomes...', category: 'Tips' },
  { id: 4, title: 'Bankroll Management: The Key to Long-term Success', excerpt: 'Essential money management techniques every serious bettor must know...', category: 'Finance' },
];

export default function BlogPreview() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl sm:text-4xl font-bold text-center text-gray-900 mb-12">Latest Sports News</h2>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {blogPosts.map((post) => (
            <article key={post.id} className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all border border-gray-100 flex flex-col">
              <div className="text-xs font-bold text-primary uppercase tracking-wider mb-3">{post.category}</div>
              <h3 className="text-xl font-bold text-gray-900 mb-4 leading-tight flex-1">
                <Link to={`/blog/${post.id}`} className="hover:text-primary transition-colors">{post.title}</Link>
              </h3>
              <p className="text-gray-600 text-sm mb-6 leading-relaxed">{post.excerpt}</p>
              <Link to={`/blog/${post.id}`} className="text-primary font-bold text-sm hover:underline">
                Read More →
              </Link>
            </article>
          ))}
        </div>

        <div className="text-center mt-12">
          <Link to="/blog" className="inline-block px-8 py-3.5 bg-primary text-white rounded-full font-bold hover:bg-primary-hover transition-all shadow-lg hover:-translate-y-0.5">
            View All Articles
          </Link>
        </div>
      </div>
    </section>
  );
}