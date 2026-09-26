import React from "react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

const links = [
  { to: "/discover", mode: null as string | null, num: "01", label: "Bench" },
  {
    to: "/discover",
    mode: "indication",
    num: "02",
    label: "Indication",
  },
  { to: "/evidence", mode: null, num: "03", label: "Literature" },
  { to: "/graph", mode: null, num: "04", label: "Neighborhood" },
];

export const Navigation: React.FC = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const indicationMode = searchParams.get("mode") === "indication";

  return (
    <nav className="flex flex-col gap-0.5 mt-6 flex-1" aria-label="Primary">
      {links.map((link) => {
        const isDiscover = link.to === "/discover";
        const isActive = isDiscover
          ? location.pathname.startsWith("/discover") &&
            (link.mode === "indication" ? indicationMode : !indicationMode) &&
            !location.pathname.startsWith("/analysis")
          : location.pathname.startsWith(link.to);

        const href =
          link.mode === "indication"
            ? "/discover?mode=indication"
            : link.to === "/discover"
              ? "/discover"
              : link.to;

        return (
          <Link
            key={`${link.num}-${link.label}`}
            to={href}
            aria-current={isActive ? "page" : undefined}
            className={`flex items-baseline gap-2.5 px-4 py-2 text-[13px] border-l-2 ${
              isActive
                ? "border-[#1A535C] bg-[#F5F5ED]/90 text-[#1A1F1C] font-medium"
                : "border-transparent text-[#4A524C] hover:bg-[#F5F5ED]/45 hover:text-[#1A1F1C]"
            }`}
          >
            <span
              className={`id-text w-5 shrink-0 text-[11px] ${
                isActive ? "text-[#1A535C]" : ""
              }`}
            >
              {link.num}
            </span>
            <span className="font-sans">{link.label}</span>
          </Link>
        );
      })}
    </nav>
  );
};
