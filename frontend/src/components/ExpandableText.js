import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const ExpandableText = ({ text, label, maxLines = 3, className = '' }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [needsExpansion, setNeedsExpansion] = useState(false);
  const textRef = useRef(null);

  useEffect(() => {
    if (textRef.current) {
      // Check if text overflows
      const lineHeight = parseInt(window.getComputedStyle(textRef.current).lineHeight);
      const maxHeight = lineHeight * maxLines;
      setNeedsExpansion(textRef.current.scrollHeight > maxHeight + 5);
    }
  }, [text, maxLines]);

  if (!text) return null;

  return (
    <div className={className}>
      {label && (
        <p className="text-xs text-purple-400 font-semibold mb-1">{label}</p>
      )}
      <div className="relative">
        <p
          ref={textRef}
          className={`text-gray-300 text-sm whitespace-pre-wrap transition-all duration-300 ${
            !isExpanded ? `line-clamp-${maxLines}` : ''
          }`}
          style={!isExpanded ? { 
            display: '-webkit-box',
            WebkitLineClamp: maxLines,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden'
          } : {}}
        >
          {text}
        </p>
        {needsExpansion && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="mt-1 text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 transition-colors"
            data-testid="expand-text-btn"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                Read more
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};

export default ExpandableText;
