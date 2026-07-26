import React, { useEffect, useRef, useState } from 'react';
import { postLearnerEvents } from './events';

export function BlockWrapper({ children, blockId, courseId, moduleId, blockType }) {
  const ref = useRef(null);
  const [viewed, setViewed] = useState(false);

  useEffect(() => {
    if (!ref.current || viewed || !courseId) return;

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setViewed(true);
        observer.disconnect();

        const eventType = blockType === "h5p" ? "H5P_STARTED" : "BLOCK_VIEWED";
        postLearnerEvents([{
          event_type: eventType,
          course_id: courseId,
          module_id: moduleId,
          ...(Number.isInteger(blockId) ? { block_id: blockId } : {})
        }]);
      }
    }, { threshold: 0.5 });

    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [viewed, courseId, moduleId, blockId, blockType]);

  return <div ref={ref}>{children}</div>;
}
