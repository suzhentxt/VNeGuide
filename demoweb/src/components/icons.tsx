import type { SVGProps } from "react";

export function PortalHomeIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg fill="currentColor" viewBox="0 0 24 24" {...props}>
      <path d="M1.7 10.4 12 2l10.3 8.4-1.5 1.8L12 5 3.2 12.2z" />
      <path d="M5 10.2 12 4.7l7 5.5V21h-5v-6h-4v6H5z" />
    </svg>
  );
}

export {
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MenuIcon,
  SearchIcon,
  XIcon,
} from "lucide-react";
