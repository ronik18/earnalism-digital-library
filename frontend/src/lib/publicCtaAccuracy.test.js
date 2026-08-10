import fs from "fs";
import path from "path";

function source(relativePath) {
  return fs.readFileSync(path.join(process.cwd(), relativePath), "utf8");
}

describe("public CTA accuracy contract", () => {
  const header = source("src/components/Header.jsx");
  const home = source("src/pages/Home.jsx");
  const hero = source("src/components/PremiumHero.jsx");
  const bookDetail = source("src/pages/BookDetail.jsx");
  const bookCard = source("src/components/BookCard.jsx");
  const pricing = source("src/pages/Pricing.jsx");
  const account = source("src/pages/Account.jsx");
  const upsell = source("src/components/Funnel/ReaderUpsellPrompt.jsx");
  const contact = source("src/pages/Contact.jsx");
  const journal = source("src/pages/Journal.jsx");
  const login = source("src/pages/Login.jsx");
  const signup = source("src/pages/Signup.jsx");
  const shareButtons = source("src/components/ShareButtons.jsx");
  const footer = source("src/components/Footer.jsx");
  const globalStyles = source("src/index.css");

  test("catalog destinations use browsing language instead of claiming that reading has started", () => {
    expect(header).toContain('to="/library" className="premium-header-cta" data-testid="header-cta-library">Browse Library');
    expect(header).toContain('data-testid="mobile-cta-library">Browse Library');
    expect(hero).toContain('? "Browse Library"');
    expect(hero).toContain('audiobooksDestination.includes("availability=approved-audiobook")');
    expect(hero).toContain('? "Approved Audiobooks"');
    expect(header).not.toContain('label: "Membership"');
    expect(header).toContain('label: "Reading Passes"');
  });

  test("home paths describe their exact language and release-gated destinations", () => {
    expect(home).toContain('label: "Browse Bengali classics"');
    expect(home).toContain('to: "/library?language=bn&availability=reader-ready"');
    expect(home).toContain('label: "Browse English classics"');
    expect(home).toContain('to: "/library?language=en"');
    expect(home).toContain('label: "Explore approved audiobooks"');
    expect(home).toContain('to: "/library?availability=approved-audiobook"');
  });

  test("Dracula detail has one truthful free-reading CTA and minute-based pass language", () => {
    expect(bookDetail).toContain('data-testid="read-preview"');
    expect(bookDetail).toContain('>Read Chapter 1 Free</Link>');
    expect(bookDetail).toContain('>View Reading Passes</Link>');
    expect(bookDetail).not.toContain("Get 7-Day Reading Pass");
    expect(bookDetail).not.toContain('isDracula ? "Continue Dracula"');
    expect(bookCard).toContain("View Passes");
  });

  test("pricing preview and account continuation lead directly to the reader", () => {
    expect(pricing).toContain('to="/reader/dracula"');
    expect(pricing).toContain("Read Chapter 1 Free");
    expect(account).toContain('to="/reader/dracula"');
    expect(account).toContain("Continue Dracula");
  });

  test("reader upsell makes no unsupported discount, coupon, or urgency claim", () => {
    expect(upsell).toContain('const checkoutPath = "/pricing?pack=1h&source=reader_finish"');
    expect(upsell).toContain("adds 60 minutes of reading time for ₹89");
    expect(upsell).toContain("View the ₹89 pass");
    expect(upsell).not.toMatch(/coupon|saving|expires|left/i);
    expect(pricing).not.toMatch(/coupon/i);
    expect(pricing).not.toContain("applied at checkout");
  });

  test("compact card CTAs retain 44px minimum touch targets", () => {
    expect(bookCard.match(/min-h-11/g)?.length).toBeGreaterThanOrEqual(5);
    expect(header).toContain("min-h-11 min-w-11");
    expect(bookDetail).toContain('className="btn-link inline-flex min-h-11');
    expect(contact).toContain('className="inline-flex h-11 w-11');
    expect(journal).toContain("min-h-11 px-4 py-2");
    expect(login).toContain("inline-flex min-h-11 items-center");
    expect(signup).toContain("inline-flex min-h-11 items-center");
    expect(shareButtons).toContain('const btn = "w-11 h-11');
    expect(footer.match(/min-h-11 min-w-11/g)?.length).toBeGreaterThanOrEqual(5);
    expect(globalStyles).toContain(".reading-dispatch__field input { width: 100%; min-height: 2.75rem;");
  });
});
