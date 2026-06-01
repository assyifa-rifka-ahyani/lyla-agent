import { Link } from "react-router-dom";
import { BmoMascot } from "../bmo/BmoMascot";
import { BmoButton } from "../bmo/BmoButton";
import { useEffect, useState } from "react";

export function HeroSection() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <section id="hero" className="relative overflow-hidden bg-gradient-to-b from-surface via-bmo-purple/10 to-surface">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 md:grid-cols-[auto_1fr] md:items-center md:py-24">
        <div
          className="flex justify-center md:justify-start"
          style={{
            animation: "bmoBounce 2.5s ease-in-out infinite",
          }}
        >
          <BmoMascot size={80} />
        </div>

        <div
          className="space-y-5 text-center md:text-left"
          style={{
            opacity: visible ? 1 : 0,
            transform: visible ? "translateY(0)" : "translateY(24px)",
            transition: "opacity 0.7s ease, transform 0.7s ease",
          }}
        >
          <h1 className="text-3xl font-medium leading-tight text-bmo-dark md:text-4xl">
            Asisten suara untuk pelajar Indonesia.
          </h1>
          <p className="max-w-xl text-base text-slate-600 md:text-lg">
            Catat tugas, ingatkan deadline, dan pantau pengeluaran — semua
            dengan suara. Taskbot mendengarkan, mencatat, dan mengingatkan
            kamu lewat BMO yang ramah.
          </p>
          <div
            className="flex flex-wrap justify-center gap-3 md:justify-start"
            style={{
              opacity: visible ? 1 : 0,
              transform: visible ? "translateY(0)" : "translateY(16px)",
              transition: "opacity 0.9s ease 0.3s, transform 0.9s ease 0.3s",
            }}
          >
            <Link to="/login">
              <BmoButton variant="primary">Mulai sekarang</BmoButton>
            </Link>
            <a href="#fitur">
              <BmoButton variant="secondary">Lihat fitur</BmoButton>
            </a>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes bmoBounce {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-12px); }
        }
      `}</style>
    </section>
  );
}