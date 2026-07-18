import { AudienceSections } from "@/components/AudienceSections";
import { HeroSearch } from "@/components/HeroSearch";
import { NewsCarousel } from "@/components/NewsCarousel";
import { PortalFooter } from "@/components/PortalFooter";
import { PortalHeader } from "@/components/PortalHeader";

export default function Home() {
  return (
    <>
      <a
        href="#noi-dung-chinh"
        className="sr-only z-[100] rounded bg-white px-4 py-2 text-[#903938] focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
      >
        Chuyển đến nội dung chính
      </a>
      <PortalHeader />
      <main id="noi-dung-chinh" className="flex-1">
        <h1 className="sr-only">Cổng Dịch vụ công Quốc gia - Bản mô phỏng Hackathon</h1>
        <HeroSearch />
        <NewsCarousel />
        <AudienceSections />
      </main>
      <PortalFooter />
    </>
  );
}
