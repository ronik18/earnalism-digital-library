import { Link } from "react-router-dom";
import { Instagram, Twitter, Linkedin, Mail } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-24 sm:mt-32 border-t border-brand bg-ivory" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-14 sm:py-20 grid grid-cols-1 md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <div className="font-serif-display text-3xl text-burgundy mb-3">The Earnalism</div>
          <p className="text-charcoal-soft max-w-md leading-relaxed">
            A boutique bookstore and self-publishing brand devoted to thoughtful business, literature, self-growth, spirituality, and Bengali reading.
          </p>
          <div className="gold-rule mt-6" />
        </div>

        <div>
          <div className="overline mb-4">Read</div>
          <ul className="space-y-2 text-charcoal-soft">
            <li><Link to="/shop" className="hover:text-burgundy transition-colors">Shop</Link></li>
            <li><Link to="/journal" className="hover:text-burgundy transition-colors">Journal</Link></li>
            <li><Link to="/about" className="hover:text-burgundy transition-colors">About</Link></li>
            <li><Link to="/publishing" className="hover:text-burgundy transition-colors">Publishing</Link></li>
            <li><Link to="/contact" className="hover:text-burgundy transition-colors">Contact</Link></li>
          </ul>
        </div>

        <div>
          <div className="overline mb-4">Reach</div>
          <a href="mailto:hello@theearnalism.com" className="flex items-center gap-2 text-charcoal-soft hover:text-burgundy">
            <Mail size={16} /> hello@theearnalism.com
          </a>
          <div className="flex gap-3 mt-5 text-charcoal-soft">
            <a href="#" aria-label="Instagram" className="hover:text-burgundy"><Instagram size={18} /></a>
            <a href="#" aria-label="Twitter" className="hover:text-burgundy"><Twitter size={18} /></a>
            <a href="#" aria-label="LinkedIn" className="hover:text-burgundy"><Linkedin size={18} /></a>
          </div>
        </div>
      </div>
      <div className="border-t border-brand">
        <div className="max-w-7xl mx-auto px-5 sm:px-8 lg:px-12 py-5 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs tracking-wider text-charcoal-soft">© {new Date().getFullYear()} The Earnalism. Read with depth.</p>
          <Link to="/admin/login" className="text-xs tracking-wider text-charcoal-soft hover:text-burgundy" data-testid="footer-admin-link">Admin</Link>
        </div>
      </div>
    </footer>
  );
}
