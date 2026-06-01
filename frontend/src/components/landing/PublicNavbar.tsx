import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BmoMascot } from "../bmo/BmoMascot";
import { BmoButton } from "../bmo/BmoButton";

export function PublicNavbar() {
  const [activeSection, setActiveSection] = useState("");

  useEffect(() => {
    const sections = ["hero", "fitur", "cara-kerja", "faq"];
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (window.scrollY === 0) {
          setActiveSection("hero");
          window.history.replaceState(null, "", window.location.pathname);
          return;
        }

        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
            if (entry.target.id === "hero") {
              window.history.replaceState(null, "", window.location.pathname);
            } else {
              window.history.replaceState(null, "", `#${entry.target.id}`);
            }
          }
        });
      },
      { rootMargin: "-20% 0px -40% 0px", threshold: 0.1 }
    );

    sections.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <nav className="sticky top-0 z-30 bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link
          to="/"
          className="flex cursor-pointer items-center gap-2 text-bmo-dark"
        >
          <BmoMascot size={28} />
          <span className="text-base font-medium">Taskbot</span>
        </Link>
        <div className="hidden items-center gap-6 md:flex">
          <a
            href="#fitur"
            className={`cursor-pointer text-sm hover:text-bmo-dark ${
              activeSection === "fitur" ? "text-bmo-dark font-semibold" : "text-slate-600"
            }`}
          >
            Fitur
          </a>
          <a
            href="#cara-kerja"
            className={`cursor-pointer text-sm hover:text-bmo-dark ${
              activeSection === "cara-kerja" ? "text-bmo-dark font-semibold" : "text-slate-600"
            }`}
          >
            Cara kerja
          </a>
          <a
            href="#faq"
            className={`cursor-pointer text-sm hover:text-bmo-dark ${
              activeSection === "faq" ? "text-bmo-dark font-semibold" : "text-slate-600"
            }`}
          >
            FAQ
          </a>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/login">
            <BmoButton variant="secondary" size="sm">
              Login
            </BmoButton>
          </Link>
        </div>
      </div>
    </nav>
  );
}