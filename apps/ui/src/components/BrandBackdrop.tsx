export const BrandBackdrop = () => {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-32 -top-24 h-[28rem] w-[28rem] rounded-full bg-[radial-gradient(circle_at_30%_20%,rgba(63,81,181,0.28),rgba(63,81,181,0))] blur-3xl opacity-80 dark:opacity-70" aria-hidden></div>
      <div className="absolute right-[-18%] top-[12%] h-[30rem] w-[30rem] rounded-[48%] bg-[radial-gradient(circle_at_70%_30%,rgba(0,43,127,0.22),rgba(0,43,127,0))] blur-3xl opacity-70 dark:opacity-60" aria-hidden></div>
      <div className="absolute bottom-[-26%] left-1/2 h-[24rem] w-[36rem] -translate-x-1/2 rotate-6 rounded-[55%] bg-[radial-gradient(circle_at_50%_50%,rgba(60,141,13,0.24),rgba(60,141,13,0))] blur-3xl opacity-60 dark:opacity-60" aria-hidden></div>
      <svg
        className="absolute inset-x-0 top-20 -z-10 h-32 text-indigoBrand/12 dark:text-indigoBrand/25"
        viewBox="0 0 1440 240"
        preserveAspectRatio="none"
        aria-hidden
      >
        <path d="M0 160c120-40 240-120 360-120s240 80 360 80 240-80 360-80 240 80 360 120v80H0z" fill="currentColor" />
      </svg>
    </div>
  );
};
