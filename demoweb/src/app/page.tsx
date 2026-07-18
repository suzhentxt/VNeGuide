import { AudienceSections } from "@/components/AudienceSections";
import { HeroSearch } from "@/components/HeroSearch";
import { NewsCarousel } from "@/components/NewsCarousel";
import { PortalFooter } from "@/components/PortalFooter";
import { PortalHeader } from "@/components/PortalHeader";

export default function Home() {
  return (
    <>
      <PortalHeader />
      <main className="flex-1">
        <HeroSearch />
        <NewsCarousel />
        <AudienceSections />
      </main>
      <PortalFooter />
    </>
  );
}
