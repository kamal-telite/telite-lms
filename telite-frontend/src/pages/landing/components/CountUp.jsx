import React, { useEffect, useRef, useState } from 'react';

export default function CountUp({ target, suffix = "", prefix = "", decimals = 0, useSeparator = true }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    let active = true;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && active) {
        let startTime = null;
        const duration = 1800; // 1.8 seconds

        const step = (currentTime) => {
          if (!startTime) startTime = currentTime;
          const progress = Math.min((currentTime - startTime) / duration, 1);
          const easeOut = 1 - (1 - progress) * (1 - progress);
          const value = easeOut * target;

          setCount(value);
          if (progress < 1 && active) {
            requestAnimationFrame(step);
          } else {
            setCount(target);
          }
        };

        requestAnimationFrame(step);
        observer.disconnect();
      }
    }, { threshold: 0.1 });

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => {
      active = false;
      observer.disconnect();
    };
  }, [target]);

  const formattedValue = decimals > 0 ? count.toFixed(decimals) : Math.floor(count);
  const displayValue = useSeparator && decimals === 0 ? Number(formattedValue).toLocaleString() : formattedValue;

  return (
    <span ref={ref}>
      {prefix}{displayValue}{suffix}
    </span>
  );
}
