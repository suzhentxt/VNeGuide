"use client";

import {
  type FocusEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import { ChevronLeftIcon, ChevronRightIcon } from "@/components/icons";
import { PORTAL_NEWS } from "@/data/portal-home";

const AUTOPLAY_DELAY_MS = 4_000;

type MotionDirection = "idle" | "from-left" | "from-right";

const modulo = (value: number, divisor: number) =>
  ((value % divisor) + divisor) % divisor;

export function NewsCarousel() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [motionDirection, setMotionDirection] =
    useState<MotionDirection>("idle");
  const [isHovered, setIsHovered] = useState(false);
  const [isFocusWithin, setIsFocusWithin] = useState(false);
  const animationFrameRef = useRef<number | null>(null);
  const isPaused = isHovered || isFocusWithin;

  const move = useCallback((step: -1 | 1) => {
    if (PORTAL_NEWS.length <= 1) {
      return;
    }

    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    setCurrentIndex((index) => modulo(index + step, PORTAL_NEWS.length));
    setMotionDirection(step > 0 ? "from-right" : "from-left");

    animationFrameRef.current = requestAnimationFrame(() => {
      animationFrameRef.current = requestAnimationFrame(() => {
        setMotionDirection("idle");
        animationFrameRef.current = null;
      });
    });
  }, []);

  useEffect(() => {
    if (
      isPaused ||
      PORTAL_NEWS.length <= 1 ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      return;
    }

    const autoplayTimer = window.setInterval(() => {
      move(1);
    }, AUTOPLAY_DELAY_MS);

    return () => window.clearInterval(autoplayTimer);
  }, [isPaused, move]);

  useEffect(
    () => () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    },
    [],
  );

  const visibleItems = Array.from(
    { length: Math.min(3, PORTAL_NEWS.length) },
    (_, slot) => {
      const itemIndex = modulo(currentIndex + slot, PORTAL_NEWS.length);

      return {
        item: PORTAL_NEWS[itemIndex],
        itemIndex,
        slot,
      };
    },
  );

  const motionClass =
    motionDirection === "idle"
      ? "translate-x-0 opacity-100 transition-[transform,opacity] duration-300 ease-out motion-reduce:transition-none"
      : motionDirection === "from-right"
        ? "translate-x-3 opacity-0"
        : "-translate-x-3 opacity-0";

  const handleBlur = (event: FocusEvent<HTMLElement>) => {
    const nextTarget = event.relatedTarget;

    if (!nextTarget || !event.currentTarget.contains(nextTarget)) {
      setIsFocusWithin(false);
    }
  };

  return (
    <section
      aria-label="Tin tức nổi bật"
      aria-roledescription="carousel"
      className="bg-[#F5F5F5] bg-[url('/target/p/home/theme/img/bg-news.jpg')] bg-cover bg-right bg-no-repeat max-[991px]:bg-none"
      onBlurCapture={handleBlur}
      onFocusCapture={() => setIsFocusWithin(true)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="region"
    >
      <div className="relative mx-auto max-w-[991px] px-[15px]">
        <div className="relative px-[30px] py-5">
          <div className="overflow-hidden">
            <div
              className={`grid grid-cols-1 min-[640px]:grid-cols-2 min-[1024px]:grid-cols-3 ${motionClass}`}
            >
              {visibleItems.map(({ item, itemIndex, slot }) => (
                <article
                  aria-label={`Tin ${itemIndex + 1} trên ${PORTAL_NEWS.length}`}
                  aria-roledescription="slide"
                  className={`min-w-0 ${
                    slot === 1
                      ? "max-[639px]:hidden"
                      : slot === 2
                        ? "max-[1023px]:hidden"
                        : ""
                  }`}
                  key={`${item.id}-${slot}`}
                  role="group"
                >
                  <div
                    className={`flex h-full flex-col px-5 ${
                      slot === 0
                        ? "min-[640px]:border-r min-[640px]:border-[#E2E2E2]"
                        : slot === 1
                          ? "min-[1024px]:border-r min-[1024px]:border-[#E2E2E2]"
                          : ""
                    }`}
                  >
                    <a
                      className="mb-2 line-clamp-2 text-base leading-tight font-bold transition-colors hover:text-[#CE7A58] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#CE7A58]"
                      href={item.href}
                    >
                      {item.title}
                    </a>
                    {item.shortDescription ? (
                      <p className="line-clamp-2 text-xs leading-5 text-[#6C757D]">
                        {item.shortDescription}
                      </p>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          </div>

          <button
            aria-label="Xem tin trước"
            className="absolute top-1/2 left-0 z-10 flex size-[30px] -translate-y-1/2 items-center justify-center text-[#1E2F41] transition-colors hover:text-[#CE7A58] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#CE7A58] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={PORTAL_NEWS.length <= 1}
            onClick={() => move(-1)}
            type="button"
          >
            <ChevronLeftIcon aria-hidden="true" className="size-6" />
          </button>

          <button
            aria-label="Xem tin tiếp theo"
            className="absolute top-1/2 right-0 z-10 flex size-[30px] -translate-y-1/2 items-center justify-center text-[#1E2F41] transition-colors hover:text-[#CE7A58] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#CE7A58] disabled:cursor-not-allowed disabled:opacity-40"
            disabled={PORTAL_NEWS.length <= 1}
            onClick={() => move(1)}
            type="button"
          >
            <ChevronRightIcon aria-hidden="true" className="size-6" />
          </button>
        </div>

        {PORTAL_NEWS.length > 0 ? (
          <p
            aria-atomic="true"
            aria-live={isFocusWithin ? "polite" : "off"}
            className="sr-only"
          >
            Tin {currentIndex + 1} trên {PORTAL_NEWS.length}:{" "}
            {PORTAL_NEWS[currentIndex].title}
          </p>
        ) : null}
      </div>
    </section>
  );
}
