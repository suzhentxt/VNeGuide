import Image from "next/image";
import {
  PORTAL_SERVICE_GROUPS_BY_TYPE,
  type PortalAudienceType,
} from "@/data/portal-home";

const audienceSections: ReadonlyArray<{
  title: string;
  tone: "citizen" | "business";
  type: PortalAudienceType;
}> = [
  {
    title: "CÔNG DÂN",
    tone: "citizen",
    type: "CITIZEN",
  },
  {
    title: "DOANH NGHIỆP",
    tone: "business",
    type: "CORPORATE",
  },
];

export function AudienceSections() {
  return (
    <section
      className="py-5 min-[769px]:py-10"
      aria-label="Dịch vụ theo đối tượng"
      data-portal-source="dichvucong.gov.vn"
    >
      <div className="mx-auto w-full max-w-[991px] px-[15px]">
        <div className="grid grid-cols-1 min-[769px]:-mx-[15px] min-[769px]:grid-cols-2">
        {audienceSections.map((group) => {
          const items = PORTAL_SERVICE_GROUPS_BY_TYPE[group.type];
          const hoverClass =
            group.tone === "citizen"
              ? "hover:bg-[rgba(103,169,159,0.15)]"
              : "hover:bg-[rgba(144,57,56,0.15)]";

          return (
            <section
              key={group.title}
              className="px-0 py-[10px] min-[769px]:px-[25px]"
              aria-labelledby={"audience-" + group.tone}
              data-audience-type={group.type}
              data-service-group-count={items.length}
            >
              <div className="relative mb-[15px] block pb-[15px] text-center text-[23px] leading-none text-[#CE7A58] after:absolute after:inset-x-0 after:bottom-0 after:h-1 after:rounded-[20px] after:bg-[#CE7A58]">
                <h2 id={"audience-" + group.tone} className="m-0 text-[23px] leading-[1.1] font-medium">
                  {group.title}
                </h2>
              </div>
              <div className="text-[18px]">
                {items.map((item) => (
                  <a
                    key={item.id}
                    href={item.href}
                    data-service-group-id={item.id}
                    data-service-group-code={item.code}
                    data-service-group-type={item.type}
                    data-service-group-order={item.order}
                    data-service-group-state={item.state}
                    className={[
                      "relative mb-[10px] block rounded-lg bg-[#F5F5F5] py-[10px] pr-5 pl-[60px] transition-colors hover:text-black focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#CE7A58]",
                      hoverClass,
                    ].join(" ")}
                  >
                    <span className="absolute top-[7px] left-[15px] h-[25px] w-[30px]">
                      <Image
                        src={item.icon}
                        alt=""
                        fill
                        sizes="30px"
                        className="object-contain object-left"
                      />
                    </span>
                    <span>{item.name}</span>
                  </a>
                ))}
              </div>
            </section>
          );
        })}
        </div>
      </div>
    </section>
  );
}
