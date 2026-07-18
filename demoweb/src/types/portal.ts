export interface NavigationItem {
  label: string;
  href?: string;
  children?: NavigationItem[];
}

export interface NewsItem {
  title: string;
  date: string;
  href: string;
}

export interface AudienceItem {
  label: string;
  icon: string;
  href: string;
}

export interface AudienceGroup {
  title: string;
  href: string;
  tone: "citizen" | "business";
  items: AudienceItem[];
}
